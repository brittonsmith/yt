"""
Dataset and related data structures.




"""

#-----------------------------------------------------------------------------
# Copyright (c) yt Development Team. All rights reserved.
#
# Distributed under the terms of the Modified BSD License.
#
# The full license is in the file COPYING.txt, distributed with this software.
#-----------------------------------------------------------------------------

import functools
import numpy as np
import weakref

@functools.total_ordering
class ParticleFile(object):
    def __init__(self, ds, io, filename, file_id, drange=None):
        self.ds = ds
        self.io = weakref.proxy(io)
        self.filename = filename
        self.file_id = file_id
        if drange is None:
            drange = (None, None)
        self.start, self.end = drange
        self.total_particles = self.io._count_particles(self)
        # Now we adjust our start/end, in case there are fewer particles than
        # we realized
        if self.start is None:
            self.start = 0
        self.end = max(self.total_particles.values()) + self.start

    def select(self, selector):
        pass

    def count(self, selector):
        pass

    def _calculate_offsets(self, fields, pcounts):
        pass

    def __lt__(self, other):
        if self.filename != other.filename:
            return self.filename < other.filename
        return self.start < other.start

    def __eq__(self, other):
        if self.filename != other.filename:
            return False
        return self.start == other.start

    def __hash__(self):
        return hash((self.filename, self.file_id, self.start, self.end))

    def _read_particle_positions(self, ptype, f=None):
        raise NotImplementedError

    def _get_particle_positions(self, ptype, f=None):
        pcount = self.total_particles[ptype]
        if pcount == 0:
            return None

        # Correct for periodicity.
        dle = self.ds.domain_left_edge.to('code_length').v
        dw = self.ds.domain_width.to('code_length').v
        pos = self._read_particle_positions(ptype, f=f)
        pos.convert_to_units('code_length')
        pos = pos.v[self.start:self.end]
        np.subtract(pos, dle, out=pos)
        np.mod(pos, dw, out=pos)
        np.add(pos, dle, out=pos)

        return pos

    def _read_particle_fields(self, ptype, field_list):
        raise NotImplementedError

    def _get_particle_fields(self, ptf, selector):
        for ptype, field_list in sorted(ptf.items()):
            pcount = self.total_particles[ptype]
            if pcount == 0:
                continue

            coords = self._get_particle_positions(ptype)
            x = coords[:, 0]
            y = coords[:, 1]
            z = coords[:, 2]
            mask = selector.select_points(x, y, z, 0.0)
            del x, y, z
            if mask is None:
                continue

            for field, data in self._read_particle_fields(ptype, field_list):
                data = data[self.start:self.end][mask]
                yield (ptype, field), data