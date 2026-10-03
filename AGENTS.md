# 本项目的编辑约定

- 先读 README.md 与 docs/编写规范.md。`book/` 是正文源；文档源在 README.md 与 docs/。index.html、阅读全文.html、完整指南.md、Skill 正文快照、about.html、文档 HTML 和 downloads/人情世故指南.pdf 都是生成文件，不直接修改。版本、日期和定位在 project.json 中维护。
- 不把情境建议写成普遍规则；不推断陌生人的动机，不添加未经支持的成功率、心理学机制或法律后果。
- 保留示例的具体性。新增条目要完整包含现有字段，并核对跨章引用。
- 如果增加研究或制度依据，提供直接出处、适用范围与日期，记录核实过程。经验建议仍需明确标注。
- 修改正文、文档或生成脚本后运行 python3 tools/build_release.py，统一生成网页、Markdown、Skill 和 PDF 并校验。引用条号随增删一起更新。仅复核现有产物可用 --check。
