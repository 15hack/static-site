select
  title,
  substr(date, 1, 10) date,
  url
from (
  select
    site,
    title,
    null description,
    date,
    url
  from
    wp_posts
  union
  select
    site,
    title,
    null description,
    date,
    url
  from
    wk_pages
  union
  select
    site,
    title,
    null description,
    date,
    url
  from
    phpbb_topics
  union
  select
    site,
    ID title,
    description,
    date,
    url
  from
    mailman_lists
) tt
where site={site}
order by date desc
