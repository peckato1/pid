"""Builds minimal in-memory GTFS ZIPs for testing."""

import io
import zipfile

_BASE = {
    "feed_info.txt": """\
feed_publisher_name,feed_publisher_url,feed_lang,feed_start_date,feed_end_date,feed_contact_email
ROPID,https://pid.cz,cs,20260418,20260501,opendata@pid.cz
""",
    "agency.txt": """\
agency_id,agency_name,agency_url,agency_timezone,agency_lang,agency_phone
1,Test Agency,https://test.cz,Europe/Prague,cs,+420123456789
""",
    "calendar.txt": """\
service_id,monday,tuesday,wednesday,thursday,friday,saturday,sunday,start_date,end_date
SVC1,1,1,1,1,1,0,0,20260418,20260501
""",
    "calendar_dates.txt": """\
service_id,date,exception_type
SVC1,20260501,1
""",
    "stops.txt": """\
stop_id,stop_name,stop_lat,stop_lon,zone_id,stop_url,location_type,parent_station,wheelchair_boarding,level_id,platform_code,asw_node_id,asw_stop_id,zone_region_type
U1Z1P,Test Stop A,50.0,14.0,P,,0,,0,,A,1,1,1
U1Z2P,Test Stop B,50.1,14.1,P,,0,,0,,B,1,2,1
""",
    "routes.txt": """\
route_id,agency_id,route_short_name,route_long_name,route_type,route_url,route_color,route_text_color,is_night,is_regional,is_substitute_transport
R1,1,1,Test Route,3,,FF0000,FFFFFF,0,0,0
""",
    "route_sub_agencies.txt": """\
route_id,route_licence_number,sub_agency_id,sub_agency_name
R1,12345,1,Test Agency
""",
    "shapes.txt": """\
shape_id,shape_pt_lat,shape_pt_lon,shape_pt_sequence,shape_dist_traveled
SH1,50.0,14.0,1,0.0
SH1,50.1,14.1,2,1.0
""",
    "trips.txt": """\
route_id,service_id,trip_id,trip_headsign,trip_short_name,direction_id,block_id,shape_id,wheelchair_accessible,bikes_allowed,exceptional,sub_agency_id,headsign_icons
R1,SVC1,TRIP1,Test Headsign,,0,,SH1,1,1,0,1,
""",
    "stop_times.txt": """\
trip_id,arrival_time,departure_time,stop_id,stop_sequence,stop_headsign,pickup_type,drop_off_type,shape_dist_traveled,trip_operation_type,bikes_allowed,stop_icons,headsign_icons
TRIP1,08:00:00,08:00:00,U1Z1P,1,,0,0,0.0,1,1,,
TRIP1,08:05:00,08:05:00,U1Z2P,2,,0,0,1.0,1,1,,
""",
    "route_stops.txt": """\
route_id,direction_id,stop_id,stop_sequence
R1,0,U1Z1P,1
R1,0,U1Z2P,2
""",
    "transfers.txt": """\
from_stop_id,to_stop_id,transfer_type,min_transfer_time,from_trip_id,to_trip_id,max_waiting_time
U1Z1P,U1Z2P,2,240,,,0
""",
}

# V2: route R1 změnila název, stop U1Z1P beze změny, přibyla R2
_V2_OVERRIDES = {
    "feed_info.txt": """\
feed_publisher_name,feed_publisher_url,feed_lang,feed_start_date,feed_end_date,feed_contact_email
ROPID,https://pid.cz,cs,20260502,20260601,opendata@pid.cz
""",
    "routes.txt": """\
route_id,agency_id,route_short_name,route_long_name,route_type,route_url,route_color,route_text_color,is_night,is_regional,is_substitute_transport
R1,1,1,Updated Route,3,,FF0000,FFFFFF,0,0,0
R2,1,2,New Route,3,,0000FF,FFFFFF,0,0,0
""",
}


def _build(overrides: dict) -> zipfile.ZipFile:
    files = {**_BASE, **overrides}
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        for name, content in files.items():
            zf.writestr(name, content)
    buf.seek(0)
    return zipfile.ZipFile(buf)


def make_zip() -> zipfile.ZipFile:
    return _build({})


def make_zip_v2() -> zipfile.ZipFile:
    return _build(_V2_OVERRIDES)
