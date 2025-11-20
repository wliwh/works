# 通用脚注处理程序

这是一个功能强大的脚注处理程序，用于自动处理文档中的脚注，包括验证、映射和插入功能。

## 功能特点

1. **自动识别和分离**：自动识别文档中的正文和脚注部分
2. **灵活的配置**：支持自定义各种脚注符号样式和输出格式
3. **严格的验证**：验证脚注编号的连续性和对应关系
4. **复杂脚注处理**：
   - 支持多个脚注符号共用同一内容
   - 自动处理脚注内容换行（使用`<br/>`替换）
5. **错误报告**：详细的错误信息帮助定位问题

## 安装和使用

### 基本使用

```python
from footnote_processor import FootnoteProcessor

# 创建处理器
processor = FootnoteProcessor()

# 处理文档
result = processor.process_document('input.txt', 'output.txt')
```

### 命令行使用

```bash
# 基本使用
python footnote_processor.py input.txt -o output.txt

# 使用配置文件
python footnote_processor.py input.txt -o output.txt -c config.json
```

### 自定义配置

```python
from footnote_processor import FootnoteProcessor, FootnoteConfig

# 创建自定义配置
config = FootnoteConfig(
    section_delimiter="========",  # 部分分隔符
    text_footnote_pattern=r'\[\[(\d+)\]\]',  # 正文中的脚注格式
    footnote_footnote_pattern=r'\[\[(\d+)\]\]',  # 脚注中的符号格式
    output_footnote_format="({content})"  # 输出格式
)

# 使用配置
processor = FootnoteProcessor(config)
result = processor.process_document('input.txt', 'output.txt')
```

## 配置选项

### FootnoteConfig 参数

- `section_delimiter`: 文档部分的开始标志（默认：`"========"`)
- `text_footnote_pattern`: 正文中脚注符号的正则表达式（默认：`r'\[\[(\d+)\]\]'`）
- `footnote_footnote_pattern`: 脚注中符号的正则表达式（默认：`r'\[\[(\d+)\]\]'`）
- `output_footnote_format`: 输出时脚注内容的格式（默认：`"({content})"`）

### 配置文件格式（JSON）

```json
{
    "section_delimiter": "========",
    "text_footnote_pattern": "\\[\\[(\\d+)\\]\\]",
    "footnote_footnote_pattern": "\\[\\[(\\d+)\\]\\]",
    "output_footnote_format": "注[{content}]"
}
```

## 支持的脚注样式

程序支持各种括号样式，例如：

1. **双方括号**：`[[1]]` → 默认样式
2. **中文方括号**：`【1】` → 设置 pattern 为 `r'【(\d+)】'`
3. **花括号**：`{{1}}` → 设置 pattern 为 `r'\{\{(\d+)\}\}'`
4. **圆括号**：`((1))` → 设置 pattern 为 `r'\(\((\d+)\)\)'`
5. **自定义样式**：通过正则表达式自定义任意格式

## 文档格式要求

### 输入文档结构

```
========部分ID
正文内容，包含脚注符号[[1]]...

更多正文内容[[2]]...

[[1]]第一个脚注的内容
[[2]]第二个脚注的内容

========下一部分ID
...
```

### 规则说明

1. **部分分隔**：每个部分以指定的分隔符开始
2. **正文优先**：每个部分总是先正文，后脚注
3. **脚注格式**：
   - 正文中：脚注符号不会出现在行首，多个符号不会连续
   - 脚注中：每行以脚注符号开头，后接内容
4. **连续编号**：脚注编号必须从1开始连续递增
5. **多符号共享**：支持`[[2]] [[3]]共同的内容`这种格式
6. **换行处理**：脚注内容的换行会被替换为`<br/>`

## 错误处理

程序会检查以下错误：

1. **编号连续性**：检查是否有遗漏或重复的编号
2. **对应关系**：验证正文和脚注的编号是否一一对应
3. **格式正确性**：确保符号格式符合配置

如果发现错误，程序会：
- 输出详细的错误信息
- 保持原文档内容不变
- 继续处理其他部分

## 示例

### 输入文档

```
========第一章
这是正文内容[[1]]，还有更多内容[[2]]。

[[1]]第一个脚注
[[2]]第二个脚注
```

### 输出结果

```
========第一章
这是正文内容(第一个脚注)，还有更多内容(第二个脚注)。
```

## 运行示例

查看 `examples.py` 文件中的完整示例：

```bash
python examples.py
```

示例包括：
1. 基本使用
2. 自定义配置
3. 错误处理
4. 复杂脚注处理
5. 配置文件使用
6. 不同括号样式

## 注意事项

1. 确保输入文档编码为 UTF-8
2. 脚注编号必须使用阿拉伯数字
3. 每个部分的脚注独立编号
4. 验证失败时会保留原内容

## 许可

MIT License
