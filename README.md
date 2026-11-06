# launchpad

> 把 GitHub 项目发到各平台，并自动向 awesome-list 投稿。

[![tests](https://github.com/xingaorpw/launchpad/actions/workflows/ci.yml/badge.svg)](https://github.com/xingaorpw/launchpad/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python 3.10+](https://img.shields.io/badge/python-3.10%2B-blue.svg)](https://www.python.org/)

---

## 它解决什么问题

项目做完了，然后呢？

你可能想在十个平台都发一遍。但**这件事有一半是做不到的**——不是技术问题，是接口问题：

| 平台 | 有发布 API？ | 能自动化？ | 原因 |
|---|---|---|---|
| Dev.to | ✅ 免费 | ✅ | 注册即用 |
| Bluesky | ✅ 免费 | ✅ | app password |
| Mastodon | ✅ 免费 | ✅ | access token |
| Telegram | ✅ Bot API | ✅ | 建个 bot 就行 |
| Discord | ✅ Webhook | ✅ | 一条 URL |
| Hashnode | ✅ GraphQL | ✅ | 免费 token |
| X / Twitter | ⚠️ 付费档 | ⚠️ | 免费额度极小 |
| Reddit | ✅ OAuth | ⚠️ | self-promo 极易被封 |
| 小红书 / 知乎 / 掘金 / 微博 | ❌ | ❌ | 无发布接口，自动化=封号 |
| Hacker News | ❌ 只读 | ❌ | 发帖必须网页 |

**自动注册账号更不可能**——手机验证码、邮箱验证、CAPTCHA，加上明确禁止自动化的服务条款。任何声称能做的工具，结果都是号被封。

所以这个项目做两件事：

1. **把能自动化的部分做到位**：一份文案 → 六个平台，长短自动适配，GitHub Actions 定时发
2. **把不能自动化的部分整理成清单**：`docs/PLAYBOOK.md`，写清每个平台该发什么、什么时候发、注意什么

还有第三件，可能是最有用的——**awesome-list 自动投稿**。往下看。

---

## 快速开始

```bash
pip install -r requirements.txt

python -m launchpad projects      # 列出所有项目
python -m launchpad platforms     # 看哪些平台配好了
python -m launchpad plan --project repo-doctor --platform bluesky   # 预览文案
python -m launchpad post --platform devto --project repo-doctor --dry-run
```

`plan` 不联网，只是把渲染结果打出来，用来调文案。

### 真实输出

```
$ python -m launchpad platforms
  平台           状态     缺什么
  ------------------------------------------------------------
  devto        ✗      DEVTO_API_KEY
  bluesky      ✗      BSKY_HANDLE, BSKY_APP_PASSWORD
  mastodon     ✗      MASTODON_BASE_URL, MASTODON_TOKEN
  telegram     ✗      TELEGRAM_BOT_TOKEN, TELEGRAM_CHAT_ID
  discord      ✗      DISCORD_WEBHOOK_URL
  hashnode     ✗      HASHNODE_TOKEN, HASHNODE_PUBLICATION_ID
```

```
$ python -m launchpad plan --project repo-doctor --platform bluesky
repo-doctor  ·  https://github.com/xingaorpw/repo-doctor

  ✗ bluesky    [短帖] 207 字符
    │ 给你的 GitHub 仓库做发布体检：13 项检查，缺什么一目了然
    │
    │ 写完代码只是开始。有没有 LICENSE、有没有 Topics、README 里有没有安装命令和截图
    │ ——这些才决定别人会不会 star 你，但没有人会告诉你漏了哪一件。
    │
    │ https://github.com/xingaorpw/repo-doctor
    │ #opensource #python
```

---

## 配置平台

每个平台只需要环境变量，**都不需要付费或人工审核**。

### Dev.to（最推荐，技术读者精准）

1. GitHub 登录 https://dev.to
2. Settings → Extensions → **DEV API Key**
3. `export DEVTO_API_KEY=...`

### Bluesky

1. 注册 https://bsky.app
2. Settings → **App Passwords** → 新建
3. `export BSKY_HANDLE=you.bsky.social` 和 `export BSKY_APP_PASSWORD=xxxx-xxxx-xxxx-xxxx`

> 用 App Password，不要用主密码。App Password 可以单独撤销。

### Mastodon

1. 实例里 Preferences → Development → New application
2. 勾 `write:statuses`
3. `export MASTODON_BASE_URL=https://mastodon.social` 和 `export MASTODON_TOKEN=...`

### Telegram

1. 找 [@BotFather](https://t.me/BotFather) 发 `/newbot`
2. 把 bot 拉进你的频道并设为管理员
3. `export TELEGRAM_BOT_TOKEN=...` 和 `export TELEGRAM_CHAT_ID=@your_channel`

### Discord

频道设置 → Integrations → Webhooks → 新建 → 复制 URL

`export DISCORD_WEBHOOK_URL=...`

### Hashnode

1. https://hashnode.com/settings/developer → 生成 token
2. 从你的 publication URL 里拿 ID
3. `export HASHNODE_TOKEN=...` 和 `export HASHNODE_PUBLICATION_ID=...`

---

## awesome-list 投稿

这是**唯一能持续带来自然流量**的自动化渠道，比在社交平台刷帖有效得多。

awesome-list 是长期排在搜索结果前面的仓库，被收录意味着之后每个月都有人从那里点进来。

```bash
# 1. 先看看有哪些候选列表、自己有没有被收录
python -m launchpad awesome scan --project repo-doctor

# 2. 预览会插入哪一行、插在哪个分节
python -m launchpad awesome submit --list vinta/awesome-python \
    --project repo-doctor --dry-run

# 3. 真开 PR
python -m launchpad awesome submit --list vinta/awesome-python --project repo-doctor
```

### 它怎么保证 PR 质量

维护者会审，所以补丁必须干净：

- **找对分节**：标题命中项目 tag 就选它，否则选条目最多的那一节
- **按字母序插入**：跟邻居保持一致的排序，而不是直接追加到末尾
- **格式跟邻居一致**：`- [名字](链接) - 一句话`
- **已收录就跳过**：不会重复开 PR

### 注意

- 一次只投一个列表，**不要批量开 PR**——那会被当成 spam
- 挑 `stars > 1000` 且最近三个月有更新的列表
- PR 描述里写清楚加的是什么、为什么值得收录
- 有些列表要求先开 issue 或用他们的模板，先读 CONTRIBUTING

---

## 定时发布

`.github/workflows/promo.yml` 每周二跑一次，按周数轮换项目，只发到**已配置**的平台。

在仓库 Settings → Secrets 里加上面那些环境变量即可。没配的平台自动跳过，不会报错。

手动触发：Actions → promote → Run workflow，可以指定项目。

---

## 手动部分

`docs/PLAYBOOK.md` 里有完整的清单：Show HN 模板、Reddit 子版和规则、小红书 / 知乎 / 掘金的文案、以及**什么时候发**。

简单说三件事，按性价比排序：

1. **一次 Show HN** —— 手动，但顶得上 1000 条自动发帖
2. **awesome-list PR** —— 本工具已自动化
3. **一篇有真东西的文章** —— 写好发 Dev.to，再手动分发到掘金

---

## 已知限制

- **中文平台全都不支持**，没有开放接口。想发只能手动，`PLAYBOOK.md` 里给了文案。
- **X / Reddit 没实现**。X 需要付费档，Reddit 的 self-promo 封号风险太高，我不想给你一个会毁号的功能。
- **不检测重复发布**。同一个项目连着跑两次会发两条，自己在 CI 里控制频率。
- **awesome-list 的分节匹配是启发式的**。README 结构千奇百怪，找不到合适分节时会直接跳过而不是乱插。
- **不做内容去重和质量评估**。文案是你自己写的，工具只负责分发。

## License

[MIT](LICENSE) © 2026 xingaorpw
