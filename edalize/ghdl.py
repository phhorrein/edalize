# Copyright edalize contributors
# Licensed under the 2-Clause BSD License, see LICENSE for details.
# SPDX-License-Identifier: BSD-2-Clause

import logging
import os.path
from edalize.edatool import Edatool

logger = logging.getLogger(__name__)


class Ghdl(Edatool):

    argtypes = ['vlogparam', 'generic']

    @classmethod
    def get_doc(cls, api_ver):
        if api_ver == 0:
            return {'description' : "GHDL is an open source VHDL simulator, which fully supports IEEE 1076-1987, IEEE 1076-1993, IEE 1076-2002 and partially the 1076-2008 version of VHDL",
                    'lists' : [
                        {'name' : 'analyze_options',
                         'type' : 'String',
                         'desc' : 'Options to use for the import (ghdl -i) and make (ghdl -m) phases'},
                        {'name' : 'run_options',
                         'type' : 'String',
                         'desc' : 'Options to use for the run (ghdl -r) phase'},
                        ]}

    def configure_main(self):
        (src_files, incdirs) = self._get_fileset_files()
        analyze_options = self.tool_options.get('analyze_options', '')

        # Check of std=xx analyze option, this overyides the dynamic determination of vhdl standard
        import re
        rx = re.compile("^--std=([0-9]+)")
        m = None
        for o in analyze_options:
            m = rx.match(o)
            if m:
                stdarg = [ m.group() ]
                analyze_options.remove(o)
                break

        if m:
          logger.warning("Analyze option "+ m.group() + " given, will override any vhdlSource-xxxx specification\n")
          standard = m.group(1)
        else:
            # ghdl does not support mixing incompatible versions
            # specifying 93c as std should allow 87 syntax
            # 2008 can't be combined so try to parse everthing with 08 std


            has87 = has93 = has08 = False
            for f in src_files:
                if f.file_type == "vhdlSource-87":
                    has87 = True
                elif f.file_type == "vhdlSource-93":
                    has93 = True
                elif f.file_type == "vhdlSource-2008":
                    has08 = True
            stdarg = []
            if has08:
                if has87 or has93:
                    logger.warning("ghdl can't mix vhdlSource-2008 with other standard version\n"+
                                   "Trying with treating all as vhdlSource-2008"
                    )
                stdarg = ['--std=08']
            elif has87 and has93:
                stdarg = ['--std=93c']
            elif has87:
                stdarg = ['--std=87']
            elif has93:
                stdarg = ['--std=93']
            else:
                stdarg = ['--std=93c']

            standard =  rx.match(stdarg[0]).group(1)


        run_options = self.tool_options.get('run_options', [])

        analyze_options=' '.join(analyze_options)

        _vhdltypes = ("vhdlSource", "vhdlSource-87", "vhdlSource-93", "vhdlSource-2008")
        libraries = set()
        ghdlimport = ""
        vhdl_sources = ""
        for f in src_files:
            if f.file_type in _vhdltypes:
                lib = ""
                lib_dir = ""
                if f.logical_name:
                    lib = ' --work='+f.logical_name
                    lib_dir = ' --workdir=./'+f.logical_name
                    libraries.add(f.logical_name)
                ghdlimport += ("\tghdl -i $(STD) $(ANALYZE_OPTIONS){lib} {lib_dir} {file}\n".format(lib=lib, lib_dir=lib_dir, file=f.name))
                vhdl_sources += (" {file}".format(file=f.name))
            elif f.file_type in ["user"]:
                pass
            else:
                _s = "{} has unknown file type '{}'"
                logger.warning(_s.format(f.name, f.file_type))

        make_libraries_directories = ""
        for l in libraries:
            make_libraries_directories += '\tmkdir -p '+l+'\n'
            analyze_options += ' -P./'+l

        self.render_template(
            'Makefile.j2',
            'Makefile',
            {
                'std' : ' '.join(stdarg),
                'toplevel' : self.toplevel,
                'vhdl_sources' : vhdl_sources,
                'standard' : standard,
                'analyze_options' : analyze_options,
                'run_options' : ' '.join(run_options),
                'make_libraries_directories' : make_libraries_directories,
                'ghdlimport' : ghdlimport
            }
        )

    def run_main(self):
        cmd = 'make'
        args = ['run']

        # GHDL doesn't support Verilog, but the backend used vlogparam since
        # edalize didn't support generic at the time. Now that generic support
        # has been added support for vlogparam is deprecated and will be
        # removed in the future. For now support either option.

        if self.vlogparam:
            logger.warning("GHDL backend support for vlogparam is deprecated and will be removed.\n"+
                           "Use generic instead."
            )

        if self.vlogparam or self.generic:
            extra_options='EXTRA_OPTIONS='
            for d in [self.vlogparam, self.generic]:
                for k,v in d.items():
                    extra_options += ' -g{}={}'.format(k,self._param_value_str(v,'"'))
            args.append(extra_options)
        self._run_tool(cmd, args)
