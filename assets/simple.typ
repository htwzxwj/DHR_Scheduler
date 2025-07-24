#import "/lib.typ": *

#let ac = none

#let mc = none
#show: project.with(
  title: "文档标题",
  author: "作者姓名",
  date: auto,
  abstract: [
    摘要内容...
  ],
  keywords: ("关键词1", "关键词2")
)

#problem[
  计算 $f(x) = x^2$ 的导数。
]

#solution[
  $f'(x) = 2x$
]

#summary[
  这里可以写总结性的内容。
]

#show table: three-line-table // 启用三线表格样式

// 然后正常使用 table 即可
#figure(
  table(
      columns: 3,
      [项目], [数值], [单位],
      [长度], [10], [cm],
      [质量], [5], [kg],
  ),
  caption: [测量数据]
)

// 行内公式
这是 $E = mc^2$ 公式。

// 带编号的公式
$ x = frac(-b plus.minus sqrt(b^2 - 4ac), 2a) $ <eq:quadratic>

// 不编号的公式
$ sum_(i=1)^n i = frac(n(n+1), 2) $

// 偏微分
$ frac(partial f, partial x) = pardiff(f, x) $