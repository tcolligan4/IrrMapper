# =============================================================================================
# Copyright 2018 dgketchum
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
# =============================================================================================

import os


def band_map():
    band_mapping = {'LC8': ['3', '4', '5', '10'],
                    'LE7': ['2', '3', '4', '6_VCID_1'],
                    'LT5': ['2', '3', '4', '6']}
    return band_mapping


if __name__ == '__main__':
    home = os.path.expanduser('~')


# ========================= EOF ================================================================