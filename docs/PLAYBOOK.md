# 发布手册

工具能自动化的部分只有一半。这份手册覆盖另一半——**必须手动、但决定成败的部分**。

---

## 核心原则

**不要六个项目同时发。** 同时发等于都没发：没人记得住，每个都只拿到零星的注意力。

**一次只推一个，间隔 3–5 天。** 推完一个观察数据，再决定下一个推哪个、怎么改文案。

**先推最有故事的那个。** 在你这六个里，是 `repo-doctor`——"我做完项目发现发布流程全是手工，于是写了个工具自动化它"，这个开头比任何技术介绍都抓人。

---

## 30 天节奏

| 时间 | 动作 | 手动/自动 |
|---|---|---|
| D-1 | 给 6 个仓库都补上 topics、description（已完成） | ✅ 已完成 |
| D-1 | 跑 `launchpad awesome scan`，列出可投稿的列表 | 自动 |
| D0 | 向 3–5 个 awesome-list 开 PR（**一次一个，隔天一个**） | 自动 |
| D1 | Dev.to 发第一篇文章（repo-doctor） | 自动 |
| D1 | Bluesky + Mastodon 发短帖 | 自动 |
| D2 | V2EX「分享创造」发帖 | 手动 |
| D3 | Show HN（**只有一次机会**） | 手动 |
| D4 | Reddit r/coolgithubprojects | 手动 |
| D7 | 小红书 / 即刻（非技术向，讲故事） | 手动 |
| D10 | 换下一个项目，重复 D1–D4 | 混合 |
| D30 | 看数据，决定要不要给某个项目加功能 | 手动 |

---

## Hacker News（Show HN）

**这是单点收益最高的渠道**，也是唯一一个"发一次顶一年"的地方。同时它只有**一次机会**——重复发同一个项目会被 flag，账号会被降权。

### 时机

- **周二到周四**，美东时间 8:00–10:00（北京时间 20:00–22:00）
- 避开周一（积压）和周五（没人看）
- 避开美国节假日

### 标题模板

```
Show HN: repo-doctor – Score your GitHub repo on the things that decide if it gets starred
```

规则：

- 必须以 `Show HN:` 开头
- 一句话，不要形容词，不要"amazing"、"simple"
- 说清楚**它做什么**，不是**它多好**
- 不要放链接到正文外的地方——URL 填仓库地址

### 正文模板

```
I kept shipping projects that nobody starred, and eventually realized the code wasn't the problem.

Missing LICENSE. No topics. README without an install command. No CI badge. Each one is small, and nobody tells you which one you missed.

repo-doctor checks 13 of these and gives a 0-100 score. It also has a --fix mode that generates the missing LICENSE / .gitignore / CI / CONTRIBUTING.

Example: it scored my own repo 84/100 — I thought it was done.

Limitations I'm aware of: it checks presence, not quality (a README with an empty "## Install" heading passes). Weights are subjective. 60 req/hr unauthenticated.

Would love feedback on what checks are missing.
```

要点：

- **先讲痛点，再讲方案**，不要一上来介绍技术栈
- **主动说限制**——HN 的人最讨厌自吹，主动认错反而加分
- **结尾问一个具体问题**，引导评论
- 前 30 分钟很关键：有人评论要立刻回

### 不要做

- ❌ 找朋友互相 upvote —— HN 能检测投票环，直接掉排名
- ❌ 发完立刻改标题 —— 会被当成操纵
- ❌ 在评论里放自己的其他项目 —— 会被当广告

---

## Reddit

| 子版 | 允许 self-promo？ | 注意 |
|---|---|---|
| r/coolgithubprojects | ✅ 就是干这个的 | 最安全，先发这里 |
| r/opensource | ✅ 但要参与讨论 | 别只发链接 |
| r/Python | ⚠️ 有 Showcase 限制 | 先读版规，通常要求周六发 |
| r/node | ⚠️ 同上 | |
| r/programming | ❌ 基本会删 | 别浪费时间 |
| r/MachineLearning | ❌ 严格 | 只收论文 |

**通用规则**：

- 发之前先看版规和置顶帖
- 标题不要用感叹号
- 正文写清楚**为什么做**，不要只贴链接
- 发完当天要回评论，不然会被当 spam

---

## 中文平台

### V2EX「分享创造」节点

最合适的技术向中文渠道，用户对独立项目友好。

```
标题：做了个工具，给自己的 GitHub 仓库打分，发现我漏了三件事

正文：
项目做完了以为就完事了，结果被人问「你这仓库没 LICENSE 啊」。

回头检查了一遍，发现漏的不止一个：没 topics、README 没有安装说明、没有 release。
这些每一件都很小，但没人会告诉你漏了哪件。

所以写了个 repo-doctor，13 项检查，0-100 分，还能 --fix 直接生成缺失的文件。

跑了一下自己的仓库：84 分 B。以为已经发布完了，其实还差三项。

https://github.com/xingaorpw/repo-doctor

欢迎拍砖，尤其是检查项的设计——权重是我拍脑袋定的。
```

要点：**先自嘲，再介绍**。V2EX 反感硬广，但接受"我踩了个坑"。

### 即刻

短，口语，带情绪。

```
给自己的 GitHub 项目做了个体检工具，跑完发现自己三个项目全都缺 LICENSE……

现在能一键补了。
```

### 掘金

发长文，和 Dev.to 同一篇（`launchpad plan --project X --platform devto` 的输出就是现成 markdown）。掘金吃 SEO，标题里带具体关键词。

### 小红书

**不要写成技术贴。** 小红书的读者不关心 CLI，关心"这个人自己做了个东西"。

图文形式：

- 封面：一张终端截图 + 大字「给自己的 GitHub 项目做了个体检」
- 第 2 张：评分结果截图
- 第 3 张：修复前后对比
- 正文：讲故事，200 字以内，末尾放仓库名（不放链接，会被限流）

### 知乎

回答「有哪些适合大学生的开源项目」这类问题，把自己的项目作为例子写进去，而不是单独开一帖。

---

## 衡量：什么算成功

别看 star 总数，看这三个：

| 指标 | 怎么看 | 健康值 |
|---|---|---|
| **来源分布** | 仓库 Insights → Traffic → Referrers | 有 3 个以上不同来源 |
| **star 转化率** | stars ÷ 访问量 | 5%–15% 正常 |
| **awesome-list 收录数** | 自己数 | 30 天内 ≥ 2 个 |

如果 Referrers 里只有一个来源，说明渠道太单一；如果访问量高但 star 低，说明 README 没说服人（跑 `repo-doctor` 看看）。

---

## 反模式

这些事做了会掉分，不是加分的：

- ❌ **六个项目同时发** —— 注意力被自己摊薄
- ❌ **同一内容发十个平台** —— 每个平台的读者画像不同，文案要改
- ❌ **找朋友刷 star** —— GitHub 会降权，且 star 数不等于用户
- ❌ **在别人的 issue 里推销** —— 会被拉黑
- ❌ **自动注册账号** —— 违反 ToS，封号
- ❌ **一天开十个 awesome-list PR** —— 会被当 spam，维护者互相通气
- ❌ **只说优点不说限制** —— 技术社区最反感这个

---

## 检查清单

发布前逐项确认：

- [ ] 仓库有 LICENSE、description、5–10 个 topics
- [ ] README 有截图、有安装命令、有真实输出
- [ ] CI 是绿的（徽章能显示 passing）
- [ ] 有至少一个 release（`v0.1.0`）
- [ ] `repo-doctor` 跑分 ≥ 85
- [ ] 文案里的数字是真实的（star 数、测试数别瞎写）
- [ ] 主动写了「已知限制」章节
- [ ] 准备好回评论——发布后 2 小时内要在线
