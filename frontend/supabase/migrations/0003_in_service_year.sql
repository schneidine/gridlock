-- Some sources give only an in-service year (the SERTP report lists Duke Energy
-- projects that way), which a `date` column can't hold without inventing a day.
-- in_service_date stays null for those rows; in_service_year carries the year.
alter table projects add column if not exists in_service_year integer;
