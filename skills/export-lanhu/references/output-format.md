# 输出格式说明

## 目录结构

```
docs/lanhu/pages/{项目名}-{yyyyMMddHH}/
├── README.md
├── meta.json
├── pages/
│   └── {页面名}/
│       └── page.json
├── designs/
│   └── {设计名}/
│       ├── schema.json
│       ├── sketch.json
│       └── preview.png
└── slices/
    └── {切图名}.png
```

## meta.json 格式

```json
{
  "source_url": "https://lanhuapp.com/...",
  "project_name": "项目名称",
  "project_id": "xxx",
  "export_time": "2026-03-20T10:30:00",
  "version_id": "abc123...",
  "page_count": 30,
  "design_count": 80,
  "slice_count": 200
}
```

## page.json 格式

每个页面的 `page.json` 包含：

```json
{
  "name": "页面名称",
  "filename": "page_1.html",
  "id": "page_id",
  "level": 0
}
```

## 设计数据格式

### schema.json

设计图的完整 Schema JSON，包含：
- 图层树结构
- 组件信息
- 样式信息

### sketch.json

设计图的 Sketch 格式数据，包含：
- 设计标注
- 尺寸信息
- 颜色值
- 字体信息

### preview.png

设计图的预览截图，PNG 格式。

## 切图格式

切图文件命名规则：`{切图名}_{倍率}.png`

示例：
- `icon_arrow_1x.png`
- `icon_arrow_2x.png`
- `icon_arrow_3x.png`
