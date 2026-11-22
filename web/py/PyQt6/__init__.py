"""Browser stand-in for PyQt6 (see web/README.md, "Qt stand-in").

Lets the unmodified desktop interface (telescope_gui/) run under Pyodide:
`qtshim.install()` must run first so matplotlib's Qt backend resolves to
qtshim.mpl_backend. Only the Qt API the desktop app uses is provided.
"""
