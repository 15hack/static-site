select
  title,
  content,
  date,
  author,
  url
from
  wp_posts
union
select
  title,
  content,
  date,
  null author,
  url
from
  wk_pages
