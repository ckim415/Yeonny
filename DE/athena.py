#athena query
CREATE EXTERNAL TABLE IF NOT EXSISTS top_tracks(
  id string,
  artist_id string,
  name string,
  popularity int,
  external_url string
) PARTITIONED BY (dt string)
STORED AS PARQUET 
tblproperties('parquet.compress'='SNAPPY')
LOCATION 's3://spotify-artists-cy/top-tracks/';