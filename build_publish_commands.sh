rm double_subtitle_videos.egg-info dist
python -m build
twine upload --repository testpypi --verbose dist/*
twine upload --repository pypi --verbose dist/*
