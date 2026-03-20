"""
蓝湖 API 封装模块
从 lanhu_mcp_server.py 的 LanhuExtractor 类提取核心 API 逻辑
"""
import httpx
from pathlib import Path
from datetime import datetime
from urllib.parse import urlparse
from typing import Optional
import json

# 常量定义
BASE_URL = "https://lanhuapp.com"
DDS_BASE_URL = "https://dds.lanhuapp.com"
CHINA_TZ_OFFSET = 8  # 东八区


class LanhuAPI:
    """蓝湖 API 客户端"""

    def __init__(self, cookie: str, timeout: int = 30):
        """
        初始化 API 客户端

        Args:
            cookie: 蓝湖认证 Cookie
            timeout: HTTP 超时秒数
        """
        headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
            "Referer": "https://lanhuapp.com/web/",
            "Accept": "application/json, text/plain, */*",
            "Cookie": cookie,
            "sec-ch-ua": '"Chromium";v="142", "Google Chrome";v="142", "Not_A Brand";v="99"',
            "sec-ch-ua-mobile": "?0",
            "sec-ch-ua-platform": '"macOS"',
            "request-from": "web",
        }
        self.client = httpx.AsyncClient(timeout=timeout, headers=headers, follow_redirects=True)

    async def close(self):
        """关闭客户端连接"""
        await self.client.aclose()

    def parse_url(self, url: str) -> dict:
        """
        解析蓝湖 URL，提取参数

        Args:
            url: 蓝湖 URL 或参数字符串

        Returns:
            包含 team_id, project_id, doc_id 的字典
        """
        if url.startswith('http'):
            parsed = urlparse(url)
            fragment = parsed.fragment
            if not fragment:
                raise ValueError("Invalid Lanhu URL: missing fragment part")
            if '?' in fragment:
                url = fragment.split('?', 1)[1]
            else:
                url = fragment

        if url.startswith('?'):
            url = url[1:]

        params = {}
        for part in url.split('&'):
            if '=' in part:
                key, value = part.split('=', 1)
                params[key] = value

        # 支持多种参数名格式
        team_id = params.get('tid') or params.get('teamId')
        project_id = params.get('pid') or params.get('projectId')
        doc_id = params.get('docId') or params.get('image_id') or params.get('imageId')

        if not project_id:
            raise ValueError("URL parsing failed: missing required param pid/projectId")
        if not team_id:
            raise ValueError("URL parsing failed: missing required param tid/teamId")

        return {
            'team_id': team_id,
            'project_id': project_id,
            'doc_id': doc_id
        }

    async def get_document_info(self, project_id: str, doc_id: str) -> dict:
        """获取文档信息"""
        api_url = f"{BASE_URL}/api/project/image"
        params = {'pid': project_id, 'image_id': doc_id}

        response = await self.client.get(api_url, params=params)
        response.raise_for_status()
        data = response.json()

        code = data.get('code')
        success = (code == 0 or code == '0' or code == '00000')
        if not success:
            raise Exception(f"API Error: {data.get('msg')} (code={code})")

        return data.get('data') or data.get('result', {})

    async def get_pages_list(self, url: str) -> dict:
        """
        获取文档的所有页面列表

        Args:
            url: 蓝湖 URL

        Returns:
            包含 pages 列表的字典
        """
        params = self.parse_url(url)
        doc_info = await self.get_document_info(params['project_id'], params['doc_id'])

        versions = doc_info.get('versions', [])
        if not versions:
            raise Exception("Document version info not found")

        latest_version = versions[0]
        json_url = latest_version.get('json_url')
        if not json_url:
            raise Exception("Mapping JSON URL not found")

        response = await self.client.get(json_url)
        response.raise_for_status()
        project_mapping = response.json()

        # 从 sitemap 获取页面列表
        sitemap = project_mapping.get('sitemap', {})
        root_nodes = sitemap.get('rootNodes', [])

        def extract_pages(nodes, pages_list, level=0):
            for node in nodes:
                page_name = node.get('pageName', '')
                url_path = node.get('url', '')
                node_id = node.get('id', '')

                if page_name and url_path:
                    pages_list.append({
                        'name': page_name,
                        'filename': url_path,
                        'id': node_id,
                        'level': level
                    })

                children = node.get('children', [])
                if children:
                    extract_pages(children, pages_list, level + 1)

        pages_list = []
        extract_pages(root_nodes, pages_list)

        return {
            'document_id': params['doc_id'],
            'document_name': doc_info.get('name', 'Unknown'),
            'project_id': params['project_id'],
            'team_id': params['team_id'],
            'version_id': latest_version.get('version_id', ''),
            'total_pages': len(pages_list),
            'pages': pages_list
        }

    async def get_design_list(self, team_id: str, project_id: str) -> list:
        """获取设计图列表"""
        api_url = f"{BASE_URL}/api/project/images"
        params = {
            'project_id': project_id,
            'team_id': team_id,
            'limit': 1000,
            'offset': 0
        }

        response = await self.client.get(api_url, params=params)
        response.raise_for_status()
        data = response.json()

        if data.get('code') != '00000':
            raise Exception(f"API Error: {data.get('msg')}")

        # API 返回 data.images 而不是 result.list
        return data.get('data', {}).get('images', [])

    async def _get_version_id_by_image_id(self, project_id: str, team_id: str, image_id: str) -> str:
        """
        通过 multi_info API 获取设计图的 version_id

        Args:
            project_id: 项目 ID
            team_id: 团队 ID
            image_id: 设计图 ID

        Returns:
            version_id 字符串

        Raises:
            Exception: 如果未找到对应的设计图或缺少 version_id
        """
        api_url = f"{BASE_URL}/api/project/multi_info"
        params = {
            "project_id": project_id,
            "team_id": team_id,
            "img_limit": 500,
            "detach": 1,
        }

        response = await self.client.get(api_url, params=params)
        response.raise_for_status()
        data = response.json()

        if data.get("code") != "00000":
            raise Exception(f"multi_info API failed: {data.get('msg', 'Unknown error')}")

        images = (data.get("result") or {}).get("images") or []
        for img in images:
            if img.get("id") == image_id:
                vid = img.get("latest_version")
                if vid:
                    return vid
                raise Exception(f"Design {image_id} has no latest_version")

        raise Exception(f"Design not found: image_id={image_id}")

    async def _fetch_dds_schema(self, version_id: str) -> dict:
        """
        调用 DDS store_schema_revise 获取 data_resource_url，再拉取 schema JSON

        Args:
            version_id: 设计图版本 ID

        Returns:
            Schema JSON 数据
        """
        dds_headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
            "Accept": "application/json, text/plain, */*",
            "Referer": "https://dds.lanhuapp.com/",
            "Cookie": self.client.headers.get("Cookie", ""),
            "Authorization": "Basic dW5kZWZpbmVkOg==",
        }

        async with httpx.AsyncClient(timeout=self.client.timeout, headers=dds_headers, follow_redirects=True) as dds_client:
            rev_url = f"{DDS_BASE_URL}/api/dds/image/store_schema_revise"
            rev_resp = await dds_client.get(rev_url, params={"version_id": version_id})
            rev_resp.raise_for_status()
            rev_data = rev_resp.json()

            if rev_data.get("code") != "00000":
                # Schema 可能不存在，返回空对象而不是抛出异常
                return {}

            schema_url = (rev_data.get("data") or {}).get("data_resource_url")
            if not schema_url:
                return {}

            schema_resp = await dds_client.get(schema_url)
            schema_resp.raise_for_status()
            return schema_resp.json()

    async def get_design_schema_json(self, image_id: str, team_id: str, project_id: str) -> dict:
        """
        获取设计图的 Schema JSON

        调用链: multi_info -> version_id -> DDS store_schema_revise -> data_resource_url -> schema

        Args:
            image_id: 设计图 ID
            team_id: 团队 ID
            project_id: 项目 ID

        Returns:
            Schema JSON 数据，失败时返回空对象
        """
        try:
            version_id = await self._get_version_id_by_image_id(project_id, team_id, image_id)
            return await self._fetch_dds_schema(version_id)
        except Exception as e:
            print(f"  ⚠️ Failed to get schema: {e}")
            return {}

    async def get_sketch_json(self, image_id: str, team_id: str, project_id: str) -> dict:
        """
        获取原始 Sketch JSON（含完整设计标注数据）

        调用链: /api/project/image (dds_status=1) -> versions[0].json_url -> fetch JSON

        Args:
            image_id: 设计图 ID
            team_id: 团队 ID
            project_id: 项目 ID

        Returns:
            Sketch JSON 数据，失败时返回空对象
        """
        api_url = f"{BASE_URL}/api/project/image"
        params = {
            "dds_status": 1,
            "image_id": image_id,
            "team_id": team_id,
            "project_id": project_id
        }

        try:
            response = await self.client.get(api_url, params=params)
            response.raise_for_status()
            data = response.json()

            if data.get('code') != '00000':
                return {}

            result = data.get('result', {})
            versions = result.get('versions', [])
            if not versions:
                return {}

            json_url = versions[0].get('json_url')
            if not json_url:
                return {}

            json_response = await self.client.get(json_url)
            json_response.raise_for_status()
            return json_response.json()
        except Exception as e:
            print(f"  ⚠️ Failed to get sketch: {e}")
            return {}

    async def get_slices_info(self, image_id: str, team_id: str, project_id: str) -> list:
        """获取切图信息"""
        api_url = f"{BASE_URL}/api/project/image_slice_categories"
        params = {
            'image_id': image_id,
            'team_id': team_id,
            'project_id': project_id
        }

        try:
            response = await self.client.get(api_url, params=params)
            response.raise_for_status()
            data = response.json()

            if data.get('code') != '00000':
                return []

            slices = []
            for category in data.get('result', {}).get('list', []):
                for item in category.get('sliceList', []):
                    slices.append({
                        'name': item.get('name', ''),
                        'url': item.get('url', ''),
                        'width': item.get('width', 0),
                        'height': item.get('height', 0),
                        'scale': item.get('scale', '1x')
                    })
            return slices
        except httpx.HTTPStatusError:
            # 404 或其他 HTTP 错误，返回空列表
            return []
        except Exception as e:
            print(f"  ⚠️ Error getting slices: {e}")
            return []
