from distutils.core import setup
import py2exe, sys

sys.argv.append('py2exe')


MANIFEST = """
<?xml version="1.0" encoding="UTF-8" standalone="yes"?>
<assembly xmlns="urn:schemas-microsoft-com:asm.v1" manifestVersion="1.0">
  <dependency>
    <dependentAssembly>
        <assemblyIdentity
            type="win32"
            name="Microsoft.Windows.Common-Controls"
            version="6.0.0.0"
            processorArchitecture="X86"
            publicKeyToken="6595b64144ccf1df"
            language="*"
        />
    </dependentAssembly>
  </dependency>
</assembly>
"""

setup(
    options = {'py2exe': {'packages': ['encodings', 'wx'],
                          'bundle_files': 1,
                          'compressed': 1,
			              'optimize': 2, 
			              'dll_excludes': ['mswsock.dll', 'powrprof.dll']
			             }},
    windows = [{'script': 'CDListPy.py',
                'icon_resources': [(1, 'ico/BeOS_BeBox_grey.ico')],
                #'other_resources': [(24, 1, MANIFEST)],
               }],
    zipfile = None,
)
