# 蓝湖 API 参考

## 认证

所有 API 请求需要在 Header 中携带 Cookie。

## 核心 API

### 获取页面列表

```
GET /api/project/image?pid={project_id}&image_id={doc_id}
```

返回文档信息和版本列表。

### 获取设计列表

```
GET /api/project/images?project_id={project_id}
```

返回项目下的所有设计图列表。

### 获取设计 Schema

```
GET /api/service_model/image_layer_tree?image_id={image_id}&team_id={team_id}&project_id={project_id}
```

返回设计图的完整 Schema JSON 数据。

### 获取 Sketch JSON

```
GET https://dds.lanhuapp.com/api/service_model/sketch?image_id={image_id}&team_id={team_id}&project_id={project_id}
```

返回设计图的 Sketch 格式 JSON 数据。

### 获取切图信息

```
GET /api/project/image_slice_categories?image_id={image_id}&team_id={team_id}&project_id={project_id}
```

返回设计图的所有切图分类和切图列表。

## URL 参数解析

蓝湖 URL 格式：
```
https://lanhuapp.com/web/#/item/project/product?tid={team_id}&pid={project_id}&docId={doc_id}
```

参数说明：
- `tid`: Team ID（团队 ID）
- `pid`: Project ID（项目 ID）
- `docId`: Document ID（文档 ID）

## 错误处理

API 返回格式：
```json
{
  "code": "00000",
  "msg": "success",
  "result": { ... }
}
```

成功码：`00000` 或 `0`
失败码：其他值
