import supervisely as sly
import src.globals as g

from src.content import Workflow

layout = Workflow().get_layout()

app = sly.Application(layout=layout)
