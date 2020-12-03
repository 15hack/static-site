select
  title,
  substr(date, 1, 10) date,
  url
from (
  select
    site,
    title,
    date,
    url
  from
    wp_posts
  union
  select
    site,
    title,
    date,
    url
  from
    wk_pages
) tt
where site={site}
order by date desc
