# Keep Training Coach

本地运行的 `Keep` 跑步训练助手，当前版本已升级为日历驱动的训练工作台。

## 当前功能

- 在首页按月查看训练日历
- 点击日期后在弹窗中查看当天计划，并记录完成情况
- 保存多组 AI 模型配置，在生成或重生成计划时选择具体模型
- 始终只保留 1 个生效中的周训练计划
- 重生成时仅替换未来且未完成的训练安排
- 在分析页查看跑步趋势、分布图、热力图和计划完成率

## Quick Start

```bash
python -m venv .venv
.venv\Scripts\activate
python -m pip install -r requirements.txt
python app.py
```

启动后访问：

```text
http://127.0.0.1:8008
```

## 页面说明

### Home

- 月历视图展示每天的训练类型与完成状态
- 点击日期可打开弹窗，查看计划详情并提交当天日志

### Plans

- 选择已保存的模型配置生成周计划
- 对当前生效计划执行“仅未来未完成项目”的重生成

### Analysis

- `Run` 数据概览
- 月度距离趋势
- 周度距离趋势
- 配速分布
- 距离分布
- 跑步热力图
- 计划完成率
- 近似 PR 摘要

### Settings

- 保存 `Keep` 账号信息
- 新增、编辑多组兼容 `OpenAI Python SDK` 调用方式的模型配置

## 配置说明

应用配置与 SQLite 数据库默认保存在本地 `app_data/` 目录。

模型配置示例：

```json
{
  "keep": {
    "phone_number": "",
    "password": ""
  },
  "models": [
    {
      "key": "openai-gpt-4o-mini",
      "label": "OpenAI GPT-4o Mini",
      "provider_name": "openai",
      "base_url": "https://api.openai.com/v1",
      "api_key": "",
      "model": "gpt-4o-mini"
    }
  ]
}
```

## Notes

- 同步与测试均可使用本地 stub，不依赖真实 `Keep` 服务或真实 AI provider
- 当前分析页默认聚焦 `Run` 类型活动
