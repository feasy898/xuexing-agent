# stray-copies-20261019

2026-10-19 重构前备份:仓库目录之外散落的学情项目文件快照,推此分支留档。

## xueqing-agent/(原位于 工作区/学情agent/xueqing-agent)
平行会话遗留的数据分片,其中 5 个 `ledger_dv2_shards` 文件不在主库
(chemistry_grade9_fill_2、physics_grade9_fill_2/4、physics_grade11_fill_3/4),
`chemistry_grade12_choice_1.json` 比主库版本新(2026-10-08 21:13 vs 20:54)。

## home-redirect-salvage/(原位于 工作区/学情agent/home/pan-ding/...)
Windows 重定向事故的抢救快照,10 个 chiopen_struct_shards 文件,
6 个为旧版(与 main 不同,以 main 为准),4 个与 main 相同。
仅作事故留证,主库数据为权威版本。

以上文件确认远端留存后,本地原件可删除。
