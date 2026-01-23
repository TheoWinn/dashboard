import inspect
from slugify import slugify as slugify_fn

print("slugify_fn:", slugify_fn)
print("module:", slugify_fn.__module__)
print("defined in:", inspect.getsourcefile(slugify_fn))