select
  '{url}' url,
  p.*
from phpbb_posts p
where site={site} and topic={topic}
order by date asc
