select
  file,
  type,
  url
from
  phpbb_media
union
select
  -- ID file,
  null file,
  type,
  url
from
  wk_media
union
select
  -- file,
  null file,
  type,
  url
from
  wp_media
