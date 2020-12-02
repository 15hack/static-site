select
  s.title,
  s.type,
  s.url,
  p.content
from
  sites s left join (
    select url, content from wp_posts where content is not null
    union
    select url, content from wk_pages where content is not null
  ) p on (
    s.url = p.url or
    (s.url || '/') = p.url or
    (p.url || '/') = s.url
  )
