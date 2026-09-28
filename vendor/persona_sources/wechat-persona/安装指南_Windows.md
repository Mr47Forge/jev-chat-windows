# 微信聊天记录分析工具 · Windows 使用指南

> ⚠️ **使用前须知**：本工具分析的是你**自己设备上**已解密的微信本地数据库，
> 全程在本地运行，AI 人格分析由 Claude Code 完成，不需要任何 API Key，不向外部发送消息内容。
> **请勿用于分析他人数据。**


---

## 前提条件

1. **Python 3.10+**
2. **已解密的微信数据库**（本工具不包含解密功能，需要你自行准备）

### 如何获取解密后的数据库

WeChat for Windows 4.x 的本地数据库是 SQLCipher 4 加密的，需要先解密。推荐使用开源工具 [ylytdeng/wechat-decrypt](https://github.com/ylytdeng/wechat-decrypt)，具体步骤请参考该项目的文档。

解密完成后，你应该得到一个目录，结构类似：

```
decrypted/
├── contact/
│   └── contact.db
├── message/
│   ├── message_0.db
│   ├── message_1.db
│   └── ...
├── head_image/
│   └── head_image.db
└── ...
```

---

## 安装

```bash
git clone https://github.com/<你的用户名>/ginger_wechat_portrait.git
cd ginger_wechat_portrait
pip install jieba wordcloud matplotlib anthropic pandas
```

> 中国大陆用户如果 pip 速度慢，加 `-i https://pypi.tuna.tsinghua.edu.cn/simple`

---

## 配置

在项目根目录创建 `config.json`，指向你的解密数据库：

```json
{
  "decrypted_db_dir": "C:/Users/你的用户名/Documents/wechat-decrypt/decrypted"
}
```

如果你的微信数据目录不在默认位置（`%USERPROFILE%\Documents\xwechat_files\`），还需要加：

```json
{
  "decrypted_db_dir": "...",
  "xwechat_files_dir": "D:/你的路径/xwechat_files"
}
```

---

## 使用

### 一对一聊天分析

```bash
# 列出所有联系人
python export_contact.py --list-contacts

# 导出指定联系人的聊天记录
python export_contact.py --contact "联系人名字"

# 生成图表 + 人格分析输入
python main.py export_contact.csv

# 用 Claude Code 完成人格分析后，生成完整对比报告
python main.py export_contact.csv \
  --personality-result wechat_analysis_output/personality_result.json \
  --partner-personality-result wechat_analysis_output/partner_result.json \
  --partner-name "联系人名字"
```

### 群聊分析

```bash
# 列出所有群
python export_group.py --list-groups

# 导出群消息（按成员拆分）
python export_group.py --group "群名片段" --top 4

# 为每位成员采样
python analyze_group_members.py group_<群名>/

# Claude Code 完成人格分析后，生成群友画像报告
python group_report.py group_<群名>/
```

---

## 常见问题

**Q：找不到联系人**
A：先跑 `python export_contact.py --list-contacts` 看看能列出哪些。如果列表为空，检查 `config.json` 里的 `decrypted_db_dir` 路径是否正确。

**Q：消息数量很少，远少于手机上的记录**
A：WeChat PC 端只存登录后收发的消息。手机上的历史记录需要通过微信的「聊天记录迁移」功能转到 PC，再重新解密。

**Q：图表中文显示为方块**
A：需要中文字体。Windows 上一般有 Microsoft YaHei，如果没有，安装任意中文字体即可。

---

## 隐私说明

- 所有数据处理在**本地**完成，不向任何外部服务发送消息内容
- AI 人格分析由 **Claude Code** 完成，不需要额外的 API Key
- 不会收集或上传任何数据
- **请勿用于分析他人设备上的数据**

---

*适用于 Windows 10/11 · WeChat for Windows 4.x · Python 3.10+*
*Forked from [姜饼探AI](https://github.com/Jiang59991/ginger_wechat_portrait) by lewer*
