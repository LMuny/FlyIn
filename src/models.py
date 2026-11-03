from pydantic import BaseModel, Field
from enum import Enum


class ZoneType(str, Enum):
    """Type of a zone, which sets how drones can move into it."""

    NORMAL = "normal"
    BLOCKED = "blocked"
    RESTRICTED = "restricted"
    PRIORITY = "priority"

    @property
    def cost(self) -> int:
        """Number of turns it takes to move into a zone of this type."""
        return 2 if self is ZoneType.RESTRICTED else 1


class Hub(BaseModel):
    """A zone on the map that drones can move through.

    Attributes:
        name: Unique name of the zone.
        x: Horizontal coordinate.
        y: Vertical coordinate.
        zone: Type of the zone, which sets its movement cost.
        color: Color used for display, or None.
        max_drones: Maximum number of drones in the zone at once.
        unlimited: True for the start and end hubs, which have no limit.
        drone_count: Number of drones currently in the zone.
    """

    name: str
    x: int = Field(ge=0)
    y: int = Field(ge=0)
    zone: ZoneType = ZoneType.NORMAL
    color: str | None = None
    max_drones: int = Field(default=1, gt=0)
    unlimited: bool = False
    drone_count: int = 0

    def has_room(self) -> bool:
        """Check if one more drone can enter this hub.

        Returns:
            True if the hub is unlimited or below max_drones.
        """
        if self.unlimited:
            return True
        return self.drone_count < self.max_drones


class Connection(BaseModel):
    """A two-way link between two hubs.

    Attributes:
        max_link_capacity: Maximum number of drones on the link at once.
        hub_a: One end of the link.
        hub_b: The other end of the link.
    """

    max_link_capacity: int = Field(ge=0)
    hub_a: Hub
    hub_b: Hub
