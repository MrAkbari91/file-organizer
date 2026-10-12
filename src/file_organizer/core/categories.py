"""Category mappings and resolution logic for files."""

from pathlib import Path
from typing import Dict, List, Optional
from file_organizer.core.utils import normalize_extension

# Standard comprehensive category mappings
DEFAULT_CATEGORIES: Dict[str, List[str]] = {
    # Images and graphics
    "Images": [
        "jpg", "jpeg", "jpe", "jfif", "png", "gif", "bmp", "dib",
        "svg", "svgz", "webp", "tif", "tiff", "ico", "cur",
        "heic", "heif", "avif", "jxl", "raw", "cr2", "cr3",
        "nef", "nrw", "arw", "srf", "sr2", "dng", "orf",
        "rw2", "raf", "pef", "srw", "psd", "psb",
        "ai", "eps", "exr", "hdr", "icns", "apng", "jp2",
        "j2k", "jpf", "jpx", "pcx", "tga", "dds",
        "emf", "wmf"
    ],

    # Documents and text
    "Documents": [
        "pdf", "doc", "docx", "docm", "dot", "dotx", "txt",
        "text", "rtf", "odt", "ott", "pages", "wps", "wpd",
        "tex", "latex", "md", "markdown", "rst", "org",
        "epub", "mobi", "azw", "azw3", "djvu", "djv",
        "xps", "oxps", "ps", "lit", "fb2", "cbz", "cbr",
        "chm", "abw", "sdw", "kwd"
    ],

    # Spreadsheets
    "Spreadsheets": [
        "xls", "xlsx", "xlsm", "xlsb", "xlt", "xltx",
        "xltm", "csv", "tsv", "ods", "ots", "numbers",
        "dif", "slk", "wk1", "wk3", "wk4"
    ],

    # Presentations
    "Presentations": [
        "ppt", "pptx", "pptm", "pps", "ppsx", "ppsm",
        "pot", "potx", "potm", "odp", "otp", "key"
    ],

    # Audio
    "Audio": [
        "mp3", "wav", "wave", "aac", "flac", "ogg", "oga",
        "m4a", "m4b", "m4p", "wma", "aiff", "aif", "aifc",
        "opus", "mid", "midi", "amr", "ape", "ac3", "dts",
        "au", "snd", "caf", "voc", "wv", "tta", "spx",
        "dsf", "dff", "ra", "ram"
    ],

    # Videos
    "Videos": [
        "mp4", "m4v", "mkv", "mov", "avi", "wmv", "flv",
        "webm", "mpeg", "mpg", "mpe", "m2v", "3gp",
        "3g2", "mts", "m2ts", "ts", "vob", "ogv", "f4v",
        "asf", "rm", "rmvb", "divx", "mxf", "roq", "nsv",
        "yuv", "amv", "mpv", "ivf"
    ],

    # Compressed files and archives
    "Archives": [
        "zip", "zipx", "rar", "7z", "tar", "gz", "gzip",
        "bz", "bz2", "xz", "zst", "lz", "lzma", "lzo",
        "lz4", "br", "cab", "arj", "ace", "alz", "arc",
        "ark", "car", "dar", "dgc", "ha",
        "lzh", "lha", "partimg", "paq6",
        "paq7", "paq8", "pea", "pim", "pit", "qda", "rar5",
        "sda", "sea", "sen", "shar", "shk", "sit", "sitx",
        "sqx", "uc", "uc0", "uc1", "uc2", "ucn", "ur2",
        "xar", "z", "zoo", "zpaq", "whl", "gem", "nupkg"
    ],

    # Programming and source code
    "Code": [
        # Python
        "py", "pyw", "pyi", "pyx", "pxd", "pxi", "ipynb",
        "pyc", "pyo",

        # JavaScript, TypeScript and Web
        "js", "mjs", "cjs", "jsx", "ts", "mts", "cts",
        "tsx", "html", "htm", "xhtml", "css", "scss",
        "sass", "less", "styl", "vue", "svelte", "astro",
        "liquid", "wasm", "map",

        # Java and JVM
        "java", "class", "jar", "war", "ear", "kt", "kts",
        "scala", "sc", "groovy", "gvy", "gy", "gsh", "clj",
        "cljs", "cljc", "edn",

        # C and C++
        "c", "h", "cc", "hh", "cpp", "hpp", "cxx", "hxx",
        "inl", "ipp", "ixx", "tpp",

        # .NET
        "cs", "csx", "vb", "vbs", "fs", "fsx", "fsi",
        "razor", "cshtml", "vbhtml",

        # Systems & Modern Languages
        "go", "rs", "rust", "zig", "nim", "nims", "cr", "v",
        "swift", "m", "mm", "dart",

        # Scripting & Dynamic
        "php", "phtml", "rb", "rake", "r", "Rmd", "pl", "pm",
        "lua", "tcl", "tk", "awk", "sed",

        # Functional & Logic
        "ex", "exs", "erl", "hrl", "hs", "lhs", "elm",
        "ml", "mli", "cl", "lisp", "scm", "ss", "rkt",
        "jl", "purs", "idr", "lean", "agda",

        # Hardware & Low level
        "sv", "svh", "vhd", "vhdl", "f", "for", "f90",
        "f95", "f03", "f08", "cob", "cbl", "adb", "ads",
        "pas", "pp", "d", "di",

        # Smart contracts & APIs
        "sol", "vy", "move", "sql", "prql", "plsql", "psql",
        "graphql", "gql", "proto", "thrift", "avsc"
    ],

    # Scripts and shell files
    "Scripts": [
        "sh", "bash", "zsh", "fish", "ksh", "csh", "bat",
        "cmd", "ps1", "psm1", "psd1", "ps1xml", "reg",
        "command", "service", "desktop"
    ],

    # Data interchange and configuration
    "Data & Config": [
        "json", "jsonc", "json5", "xml", "xsd", "xsl",
        "xslt", "dtd", "yaml", "yml", "toml", "ini", "cfg",
        "conf", "config", "properties", "env", "dotenv",
        "lock", "log", "plist", "manifest", "editorconfig",
        "gitignore", "gitattributes", "npmrc", "nvmrc",
        "browserslistrc", "babelrc", "eslintrc", "prettierrc",
        "tf", "tfvars", "hcl", "nix", "dhall", "cue",
        "ron", "ndjson", "jsonl", "msgpack",
        "avro", "parquet", "orc", "feather", "arrow"
    ],

    # Databases
    "Databases": [
        "db", "db3", "sqlite", "sqlite3", "s3db", "sl3",
        "mdb", "accdb", "mdf", "ldf", "bak", "ibd", "ibdata",
        "myd", "myi", "frm", "dbf", "realm", "rdb",
        "dump", "sqlitedb", "pdb", "fdb", "gdb", "kdb",
        "kdbx", "sdf", "bson", "wal", "shm"
    ],

    # Fonts
    "Fonts": [
        "ttf", "otf", "woff", "woff2", "eot", "fon",
        "fnt", "pfb", "pfm", "afm", "sfd", "ufo"
    ],

    # 3D and CAD engineering
    "3D & CAD": [
        "obj", "stl", "fbx", "blend", "blend1", "gltf", "glb",
        "3ds", "dae", "3mf", "amf", "ply", "step", "stp",
        "iges", "igs", "dwg", "dxf", "ifc", "skp", "max",
        "ma", "mb", "abc", "usd", "usda", "usdc", "usdz",
        "wrl", "vrml", "x3d", "sldprt", "sldasm", "slddrw",
        "ipt", "iam", "idw", "f3d", "f3z", "3dm", "shapr",
        "gcode", "nc", "3dp"
    ],

    # UI, Vector and Graphic Design
    "Design": [
        "fig", "sketch", "xd", "indd", "indt", "idml",
        "afdesign", "afpub", "afphoto", "cdr", "cmx",
        "vsd", "vsdx", "vssx", "vstx", "drawio",
        "excalidraw", "xcf", "kra", "ora", "procreate",
        "ase", "aseprite", "clip", "sai", "sai2", "pdn"
    ],

    # Disk images and Virtual Machines
    "Disk Images & Virtual Machines": [
        "iso", "img", "vhd", "vhdx", "vmdk",
        "vdi", "vma", "qcow", "qcow2", "ova",
        "ovf", "vbox", "vbox-prev", "vbox-extpack",
        "vmx", "vmxf", "vmsd", "vmsn", "vmsw",
        "hdd", "pvm", "wim", "esd", "sparseimage",
        "sparsebundle", "udf", "nrg"
    ],

    # Installers and executables
    "Executables & Installers": [
        "exe", "msi", "msp", "mst", "com", "scr", "dll",
        "sys", "ocx", "cpl", "drv", "efi", "app", "appx",
        "appxbundle", "msix", "msixbundle", "dmg", "pkg",
        "deb", "rpm", "apk", "apks", "xapk", "aab", "ipa",
        "xap", "appimage", "run", "bin", "elf", "so",
        "dylib", "out", "o", "lib", "a", "pyd", "node"
    ],

    # Email and calendars
    "Email & Calendar": [
        "eml", "msg", "mbox", "pst", "ost", "ics", "ical",
        "vcf", "vcard", "oft", "icsx"
    ],

    # Backup and temporary files
    "Backups & Temporary": [
        "backup", "old", "orig", "tmp", "temp",
        "swp", "swo", "swn", "part", "partial", "crdownload",
        "download", "cache", "dmp", "core", "stackdump"
    ],

    # Subtitles and playlists
    "Subtitles & Playlists": [
        "srt", "vtt", "ass", "ssa", "sub", "idx", "smi",
        "sami", "lrc", "ttml", "dfxp", "mpl", "mpl2",
        "m3u", "m3u8", "pls", "asx", "xspf", "wpl",
        "cue", "str"
    ],

    # Game assets and saves
    "Games": [
        "pak", "pck", "assets", "asset", "bundle", "unity3d",
        "uasset", "umap", "sav", "save", "rom", "nes",
        "sfc", "smc", "gba", "gbc", "nds", "nsp", "xci",
        "wad", "bsp", "mdl", "vpk", "dem", "replay"
    ],

    # Scientific and specialist formats
    "Scientific & Specialized": [
        "fits", "fit", "fts", "dcm", "dicom", "nii", "nii.gz",
        "mha", "mhd", "nrrd", "pdb", "mol", "mol2", "sdf",
        "xyz", "cif", "h5", "hdf5", "nc", "grib", "grb",
        "mat", "rds", "rda", "sas7bdat", "dta",
        "por", "arff", "pkl", "pickle", "joblib", "onnx",
        "pt", "pth", "safetensors", "pb", "tflite",
        "model", "weights", "ckpt"
    ],
}


def build_extension_map(categories: Optional[Dict[str, List[str]]] = None) -> Dict[str, str]:
    """Invert categories mapping so lookup by extension is O(1)."""
    mapping = categories or DEFAULT_CATEGORIES
    ext_to_cat: Dict[str, str] = {}
    for category, extensions in mapping.items():
        for ext in extensions:
            ext_to_cat[ext.lower().lstrip(".")] = category
    return ext_to_cat


# Pre-built lookup table
EXTENSION_TO_CATEGORY: Dict[str, str] = build_extension_map()


def get_file_category(
    file_path: Path,
    custom_categories: Optional[Dict[str, List[str]]] = None,
    fallback_folder: str = "Others",
) -> str:
    """
    Get the category folder name for a given file.
    If the extension is not mapped, returns fallback_folder (default 'Others').
    """
    ext = normalize_extension(file_path)
    if not ext:
        return fallback_folder

    if custom_categories:
        ext_map = build_extension_map(custom_categories)
        return ext_map.get(ext, fallback_folder)

    return EXTENSION_TO_CATEGORY.get(ext, fallback_folder)
