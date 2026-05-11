import enum


class ZoneRegionType(enum.IntEnum):
    # Auxiliary zone, not a public stop
    AUXILIARY = 0
    # Stop inside Prague
    PRAGUE = 1
    # Stop in Central Bohemia outside Prague
    CENTRAL_BOHEMIA = 2
    # Stop outside both Prague and Central Bohemia, but still part of PID
    PID_FULL = 3
    # Stop outside both Prague and Central Bohemia, usable with PID fares only if travelling through lower enum values, i.e. from Prague or Central Bohemia
    PID_TRANSIT = 4
    # Not allowed to use PID fares
    PID_NONE = 5


class StopLocationType(enum.IntEnum):
    # (or Platform). A location where passengers board or disembark from a transit vehicle. Is called a platform when defined within a parent_station.
    STOP = 0
    # A physical structure or area that contains one or more platform.
    STATION = 1
    # A location where passengers can enter or exit a station from the street. If an entrance/exit belongs to multiple stations, it may be linked by pathways to both, but the data provider must pick one of them as parent.
    ENTRANCE_EXIT = 2
    # A location within a station, not matching any other location_type, that may be used to link together pathways define in pathways.txt.
    GENERIC_NODE = 3
    # A specific location on a platform, where passengers can board and/or alight vehicles.
    BOARDING_AREA = 4


class WheelchairBoarding(enum.IntEnum):
    UNKNOWN = 0
    SOME_VEHICLES = 1
    NOT_POSSIBLE = 2
    SOME_ACCESSIBLE_PATH_FROM_OUTSIDE_TO_PLATFORM = 3
    NO_ACCESSIBLE_PATH_FROM_OUTSIDE_TO_PLATFORM = 4
    ENTRANCE_ACCESSIBLE = 5
    NO_ACCESSIBLE_PATH_FROM_ENTRANCE_TO_PLATFORM = 6


class TripOperationType(enum.IntEnum):
    # Regular trip
    REGULAR = 1
    # Depot trip (from) outside of the regular trip
    FROM_DEPOT = 7
    # Depot trip (to) outside of the regular trip
    TO_DEPOT = 8
    # Non-revenue movement on the same line, off the regular route
    LINE_TRANSFER_SAME_LINE = 9
    # Non-revenue movement to a different line
    LINE_TRANSFER_OTHER_LINE = 10


class BikesAllowed(enum.IntEnum):
    # No information
    UNKNOWN = 0
    # Bikes allowed
    ALLOWED = 1
    # Bikes not allowed
    NOT_ALLOWED = 2
    # Bikes allowed, but not able to enter or exit at this stop
    ALLOWED_NO_ENTRY_EXIT = 3
    # Bikes allowed but no entry at this stop
    ALLOWED_NO_ENTRY = 4
    # Bikes allowed but no exit at this stop
    ALLOWED_NO_EXIT = 5


class TransferFlags(enum.StrEnum):
    METRO_A = "Ma"
    METRO_B = "Mb"
    METRO_C = "Mc"
    METRO_D = "Md"
    RAILWAY = "Ra"
    RAILWAY_SUBURBAN = "Sb"
    FUNICULAR = "Fu"
    FERRY = "Fe"
    AIRPORT = "Ap"
    TRAM = "Tr"
    TROLLEYBUS = "Tb"
    BUS = "Bu"


class RouteType(enum.IntEnum):
    TRAM = 0
    SUBWAY = 1
    RAIL = 2
    BUS = 3
    FERRY = 4
    CABLE_TRAM = 5
    AERIAL_LIFT = 6
    FUNICULAR = 7
    TROLLEYBUS = 11
    MONORAIL = 12


class ExceptionType(enum.IntEnum):
    ADDED = 1
    REMOVED = 2


class PaymentMethod(enum.IntEnum):
    ON_BOARD = 0
    BEFORE_BOARDING = 1


class TransferType(enum.IntEnum):
    RECOMMENDED = 0
    TIMED = 1
    MINIMUM_TIME = 2
    NOT_POSSIBLE = 3


class PathwayMode(enum.IntEnum):
    WALKWAY = 1
    STAIRS = 2
    MOVING_SIDEWALK = 3
    ESCALATOR = 4
    ELEVATOR = 5
    FARE_GATE = 6
    EXIT_GATE = 7


class WheelchairAccessible(enum.IntEnum):
    UNKNOWN = 0
    ACCESSIBLE = 1
    NOT_ACCESSIBLE = 2


class VehicleWheelchairAccessible(enum.IntEnum):
    # from gtfs-realtime.proto
    NO_VALUE = 0
    UNKNOWN = 1
    ACCESSIBLE = 2
    NOT_ACCESSIBLE = 3


class PickupType(enum.IntEnum):
    # Regular
    REGULAR = 0
    # No pickup
    NO_PICKUP = 1
    # Must phone agency to arrange pickup
    MUST_PHONE = 2
    # Must coordinate with driver to arrange pickup
    MUST_COORDINATE_WITH_DRIVER = 3


class DropOffType(enum.IntEnum):
    # Regular
    REGULAR = 0
    # No drop off
    NO_DROP_OFF = 1
    # Must phone agency to arrange drop off
    MUST_PHONE = 2
    # Must coordinate with driver to arrange drop off
    MUST_COORDINATE_WITH_DRIVER = 3


class TripExceptional(enum.IntEnum):
    REGULAR = 0
    DEPOT_TRAM_OR_TOURIST_TRAIN = 1


class Direction(enum.IntEnum):
    OUTBOUND = 0
    INBOUND = 1


class ScheduleRelationship(enum.IntEnum):
    # from gtfs-realtime.proto TripDescriptor.ScheduleRelationship
    SCHEDULED = 0
    ADDED = 1
    UNSCHEDULED = 2
    CANCELED = 3
    REPLACEMENT = 5
    DUPLICATED = 6
    DELETED = 7
    NEW = 8
