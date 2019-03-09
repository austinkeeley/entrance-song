create view owner_device_songs as
select owner.name, 
       device.friendly_name , 
       song.artist || ' - ' || song.title as 'song' 
from owner, song, device 
where owner.id = song.owner_id and 
      device.owner_id = owner.id;

