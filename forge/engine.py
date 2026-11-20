"""Which model renders a Forge job. Shared by render_one.py and get_models.py so they can't disagree."""


def uses_klein(job):
    """FLUX.2 klein (edit model): Magic edit by default, and Expand when the job asks for it.
    New background sends edit + engine "flux": its mask is the whole background and klein keeps the cut-out's
    alpha, so the new scene came back transparent (Nov 19)."""
    mode, eng = job.get("mode", "new"), job.get("engine")
    return (mode == "edit" and eng != "flux") or (mode == "expand" and eng == "klein")
