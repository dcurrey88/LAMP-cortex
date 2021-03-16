from ..feature_types import primary_feature
from ..raw.accelerometer import accelerometer

@primary_feature(
    name="cortex.screen_state",
    dependencies=[accelerometer]
)
def screen_state(**kwargs):
    """
    TODO
    """
    return []
