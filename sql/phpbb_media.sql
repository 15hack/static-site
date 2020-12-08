select
  m.*,
  case
    when type like 'image/%' then 1
    else 0
  end image
from phpbb_media m
where site={site} and topic={topic} and post={post}
order by date asc
