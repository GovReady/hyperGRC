# The files in this example use some non-conformant changes to the
# OpenControl file formats. This script undoes those changes.

import glob
import os.path
import rtyaml

# Component files can list other files that hold control narratives.
# Put them back into the main component file.
def get_file_content(component_fn, controls_fn):
	controls_fn = os.path.join(os.path.dirname(component_fn), controls_fn)
	with rtyaml.edit(controls_fn) as controls:
		return controls.get("satisfies", [])
for fn in glob.glob("components/*/component.yaml"):
	with rtyaml.edit(fn) as component:
		if "satisfies" in component:
			satisfies = []
			for item in component['satisfies']:
				satisfies.extend(get_file_content(fn, item))
			component['satisfies'] = satisfies