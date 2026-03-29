# Keep Training Coach

本地运行的 `Keep` 跑步训练助手，当前版本已经升级为日历驱动的训练工作台，支持 `Keep` 同步、训练计划生成、活动明细、轨迹导出和中英文切换。

## 当前功能

- 首页优先展示整月训练日历，点击日期可记录当天训练日志
- `Plans` 页异步生成或重生成训练计划，任务完成后全站右上角提示
- 保存多组 AI 模型配置，在生成或重生成计划时选择具体模型
- 始终只保留 1 个生效中的训练计划，重生成时仅替换未来且未完成的训练安排
- `Analysis` 页查看跑步趋势、热力图、年度统计、地点统计和近似 `PB`
- `Activities` 页查看每一条同步活动，点进详情后可看轨迹预览
- 支持导出单条活动的 `GPX`
- 支持导出隐私版 `GPX`，默认裁掉起点和终点各 `200 m`
- 支持中英文界面切换，计划生成语言跟随当前界面语言

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
- 点击日期可打开紧凑弹窗，查看计划详情并提交当天日志
- 首页可直接发起 `Keep` 同步

### Plans

- 选择已保存的模型配置生成计划
- 支持 `rolling_week` 和 `race_goal` 两种规划类型
- 对当前生效计划执行“仅未来未完成项目”的重生成
- 生成过程为后台任务，不阻塞页面使用

### Analysis

- `Run` 数据概览
- 月度距离趋势
- 周度距离趋势
- 配速分布
- 距离分布
- GitHub 风格跑步热力图
- 计划完成率
- 年度统计
- 地点统计
- 近似 `PB` 摘要

### Activities

- 查看每一条同步跑步记录
- 活动详情页展示距离、用时、配速、心率、爬升和轨迹预览
- 支持导出标准 `GPX`
- 支持导出隐私版 `GPX`

### Settings

- 保存 `Keep` 账号信息
- 新增、编辑多组兼容 `OpenAI Python SDK` 调用方式的模型配置
- 支持中英文界面切换
- 模型配置使用下拉选择和弹窗编辑

## 配置说明

应用配置、SQLite 数据库和同步数据默认保存在本地 `app_data/` 目录，不会自动上传。

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

## 数据同步说明

- 当前同步默认聚焦 `Keep` 跑步记录
- 新同步的活动会解析并保存轨迹点与地点元数据
- 如果你是从旧版本升级，建议手动再点一次 `Sync Keep`，这样旧记录也会回补轨迹和地点信息

## 导出说明

- `Export GPX`：导出完整轨迹
- `Export Private GPX`：仅影响导出文件，不会修改数据库中的原始轨迹
- 私密导出默认裁掉首尾各 `200 m`
- 如果轨迹过短，不满足裁剪条件，会直接拒绝导出而不是泄露原始起终点

## Notes

- `Keep` 账号、模型 `API Key` 和本地数据库默认都保存在 `app_data/`，该目录应保持忽略提交
- 同步与测试均可使用本地 stub，不依赖真实 `Keep` 服务或真实 AI provider
- 当前分析页默认聚焦 `Run` 类型活动
