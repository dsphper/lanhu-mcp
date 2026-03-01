# 更新日志 / Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### 🎉 Initial Release Features

#### ✨ Added
- **需求文档分析**
  - 支持 Axure 原型自动提取和解析
  - 三种分析模式：开发视角、测试视角、快速探索
  - 四阶段工作流（全局扫描 → 分组分析 → 反向验证 → 生成交付物）
  - 智能缓存机制（基于文档版本号）
  - 页面截图和文本提取

- **UI 设计支持**
  - UI 设计图批量下载和展示
  - 切图自动识别和导出
  - 智能文件命名（基于图层路径）
  - 设计元数据提取（颜色、透明度、阴影等）

- **团队协作留言板**
  - 项目级和全局留言板
  - 五种消息类型（normal/task/question/urgent/knowledge）
  - @提醒功能（支持飞书机器人通知）
  - 协作者追踪
  - 消息搜索和筛选（支持正则表达式）
  - 消息编辑和删除
  - 10个标准元数据字段自动关联

- **性能优化**
  - 基于版本号的永久缓存
  - 增量资源更新
  - 并发下载和处理
  - 智能文件完整性检查

- **安全机制**
  - Task 类型消息的安全限制（只读查询）
  - Cookie 环境变量配置
  - 用户身份识别（从 URL 参数）
  - 角色归一化映射

#### 📖 Documentation
- 详细的中英文 README
- 贡献指南（CONTRIBUTING.md）
- MIT 开源许可证
- Docker 部署支持

#### 🛠️ Infrastructure
- FastMCP 框架集成
- Playwright 浏览器自动化
- HTTPx 异步 HTTP 客户端
- BeautifulSoup HTML 解析
- 飞书 Webhook 集成

---

## Future Roadmap

### v1.1.0 (计划中)
- [ ] 支持 Figma 设计平台
- [ ] 支持 Sketch 文件解析
- [ ] 增加 Web 管理界面
- [ ] 支持更多消息板功能（回复、点赞、标签）

### v1.2.0 (计划中)
- [ ] AI 辅助工时估算
- [ ] 技术栈智能推荐
- [ ] API 文档自动生成
- [ ] 前后端工作量分析

### v2.0.0 (计划中)
- [ ] 企业级权限管理
- [ ] 多租户支持
- [ ] 审计日志
- [ ] 性能监控和告警
- [ ] 国际化支持（更多语言）

---

## Version History

### [1.1.0] - 2026-02-27

#### 设计图分析能力升级（Design Analysis）
- **设计图分析能力质的提升**
  - 分析设计图时可获取**详细设计参数**：组件尺寸、间距、颜色值、字体大小等精确数值，便于还原设计
  - **设计图转代码**：自动将蓝湖设计 Schema 转为 HTML+CSS，与蓝湖原生导出效果对齐，AI 可直接参考实现
  - 支持按**序号**（如 `6` 表示第 6 个）或**完整名称**（如 `6_friend页_挂件墙`）指定要分析的设计图
  - 返回结果中图片与代码一一对应，便于 AI 关联视觉与实现
- 新增依赖：htmlmin（HTML 压缩）

### [1.0.0] - 2025-12-17

#### 🎉 首次发布

首个开源版本，包含核心功能：
- ✅ Axure 原型分析
- ✅ UI 设计图查看
- ✅ 切图导出
- ✅ 团队留言板
- ✅ 飞书通知集成

---

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for details on how to contribute to this project.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

<!-- Last checked: 2026-03-01 05:16 -->
