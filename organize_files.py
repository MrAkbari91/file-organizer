import argparse
import os
import shutil


def organize_files(folder):
    # Script ની પોતાની file (એને move નહીં કરવી)
    script_path = os.path.abspath(__file__)

    # Folder ની બધી files
    for filename in os.listdir(folder):
        file_path = os.path.join(folder, filename)

        # માત્ર files process કરવી
        if not os.path.isfile(file_path):
            continue

        # Script પોતે હોય તો skip
        if os.path.abspath(file_path) == script_path:
            continue

        # File extension કાઢવી
        extension = os.path.splitext(filename)[1].lower().replace(".", "")

        # Extension નથી તો skip
        if not extension:
            continue

        # Extension પ્રમાણે folder બનાવવો
        extension_folder = os.path.join(folder, extension)
        os.makedirs(extension_folder, exist_ok=True)

        # File move કરવી
        destination = os.path.join(extension_folder, filename)

        # Same નામની file હોય તો overwrite નહીં કરે
        if os.path.exists(destination):
            print(f"Skipped (already exists): {filename}")
            continue

        shutil.move(file_path, destination)
        print(f"Moved: {filename} -> {extension}/")

    print("\nDone!")


def main():
    parser = argparse.ArgumentParser(
        description="Sort files into subfolders based on their extension."
    )
    # Folder ન આપ્યો હોય તો જે folder માં script છે એ folder
    parser.add_argument(
        "folder",
        nargs="?",
        default=os.path.dirname(os.path.abspath(__file__)),
        help="folder to organize (default: the folder containing this script)",
    )
    args = parser.parse_args()

    if not os.path.isdir(args.folder):
        parser.error(f"not a folder: {args.folder}")

    organize_files(args.folder)


if __name__ == "__main__":
    main()
