# 项目修改记录

## 1. StockList 表格表头固定

### 问题
表格内容滚动时，表头需要保持固定。

### 解决方案
在 Table 组件上添加 `maxHeight` 限制表格高度。

**修改：**
```jsx
<div className="table-scroll" style={{ maxHeight: 'calc(100vh - 200px)' }}>
```

### 文件
- `frontend/src/views/StockList.tsx`

---

## 2. StockList 页面布局重构

### 问题
右侧面板顶部需要与左侧面板顶部对齐。

### 解决方案
重新划分 div 结构，让左右容器使用相同的 `card` + `card-header` 结构，自然对齐。

**修改前：**
```jsx
<div style={{ flex: 1, maxWidth: 400 }}>
  <h2>{t('stocks.title')}</h2>
  <div className="card">...</div>
</div>
<div style={{ flex: 2, paddingTop: 52 }}>...</div>
```

**修改后：**
```jsx
<div style={{ flex: 1, maxWidth: 400 }}>
  <div className="card">
    <div className="card-header">
      <div className="card-title">{t('stocks.title')}</div>
    </div>
    <div className="table-scroll">...</div>
  </div>
</div>
<div style={{ flex: 2 }}>...</div>
```

### 文件
- `frontend/src/views/StockList.tsx`

---

## 2. tsconfig 配置修复

### 问题
VS Code 提示 tsconfig.node.json 配置错误：
1. `may not disable emit`
2. `must have setting "composite": true`

### 解决方案
在 `tsconfig.node.json` 中：
- 添加 `composite: true`
- 移除 `noEmit: true`（与 composite 冲突）

**修改后 `tsconfig.node.json`：**
```json
{
  "compilerOptions": {
    "target": "ES2022",
    "lib": ["ES2023"],
    "module": "ESNext",
    "skipLibCheck": true,
    "moduleResolution": "bundler",
    "isolatedModules": true,
    "moduleDetection": "force",
    "strict": true,
    "composite": true
  },
  "include": ["vite.config.ts"]
}
```

### 文件
- `frontend/tsconfig.node.json`

---

## 3. 股票列表选中高亮功能

### 功能
选中股票时，股票代码和名称变为指定颜色。

### 实现

**步骤1：** 在样式表添加选中颜色变量
```scss
--selected: #E9ECFC;
```

**步骤2：** 在 StockList 组件中应用颜色
```jsx
<td className="mono" style={{ color: selected === s.symbol ? 'var(--selected)' : 'var(--accent)' }}>
  {s.symbol}
</td>
<td style={{ color: selected === s.symbol ? 'var(--selected)' : undefined }}>
  {s.name || '-'}
</td>
```

### 文件
- `frontend/src/styles/index.scss`
- `frontend/src/views/StockList.tsx`

---

## 修改文件清单

| 文件 | 修改类型 |
|------|----------|
| `frontend/src/views/StockList.tsx` | 重构布局 + 添加选中高亮 |
| `frontend/tsconfig.node.json` | 修复配置错误 |
| `frontend/src/styles/index.scss` | 添加 `--selected` 颜色变量 |
