# append-only-log

> 一句话（剥名后的表述）：只追加不修改，用历史换取可回溯和并发安全

- 状态：已确认
- 完整度：完整
- 例证数：2

## 三面
- **体验面**：随时能回到过去任一版本
- **设计面**（为了 A 放弃了 B）：为了可回溯，放弃原地修改的空间效率
- **实现面**（写到 `path:line`）：`src/log.rs:42` 只追加写入

## 例证
1. [[tj-commander.js]]：命令历史
2. [[jj-vcs-jj]]：操作日志

## 连接
- 同源异形：[[event-sourcing]]
- 张力：[[compaction]]（见 [[tensions]]）
- 依赖：[[content-addressing]]
