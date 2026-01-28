# -------------------------------------------------------------------------------------------------
#  Copyright (C) 2015-2026 Nautech Systems Pty Ltd. All rights reserved.
#  https://nautechsystems.io
#
#  Licensed under the GNU Lesser General Public License Version 3.0 (the "License");
#  You may not use this file except in compliance with the License.
#  You may obtain a copy of the License at https://www.gnu.org/licenses/lgpl-3.0.en.html
#
#  Unless required by applicable law or agreed to in writing, software
#  distributed under the License is distributed on an "AS IS" BASIS,
#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#  See the License for the specific language governing permissions and
#  limitations under the License.
# -------------------------------------------------------------------------------------------------


_OBJECT_TO_DICT_MAP = {}
_OBJECT_FROM_DICT_MAP = {}
_EXTERNAL_PUBLISHABLE_TYPES = set()


cdef class Serializer:
    """
    The base class for all serializers.
    """

    def __init__(self):
        super().__init__()

    cpdef bytes serialize(self, object obj):
        raise NotImplementedError("method `serialize` must be implemented in the subclass")

    cpdef object deserialize(self, bytes obj_bytes):
        raise NotImplementedError("method `deserialize` must be implemented in the subclass")
