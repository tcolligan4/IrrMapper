# IrrMapper
Automate Mapping of Irrigated Lands

Installation Instructions:

This package is a little difficult to create a working python interpreter for.

First, get [Anaconda](anaconda.org) and [git](https://git-scm.com/), these tools
are important here.

Next, create your environment.

``` conda create -n irri python=3.6```

Then get the latest gdal:

``` conda install -c conda-forge gdal=2.2.3```

Then the latest master branch of rasterio:

```pip install git+https://github.com/mapbox/rasterio.git```

Install Metio:

```pip install git+https://github.com/tcolligan4/Metio.git```

Install SatelliteImage:

```pip install git+https://github.com/dgketchum/satellite_image.git```


inclusion of CDL as a training band did not significantly affect accuracy

next ideas:

   single scene training [ ] with julian day as a feature
   two-headed net with an (L1 or L2) loss on the CDL branch [ ]
