def replace_game_type(file_path) -> bool:
    try:
        with open(file_path, 'r') as file:
            lines = file.readlines()

        found = False
        for i, line in enumerate(lines):
            if 'type multiplayer_only' in line:
                lines[i] = line.replace('multiplayer_only', 'singleplayer_only')
                found = True

        if found:
            with open(file_path, 'w') as file:
                file.writelines(lines)
            return True
        else:
            return False

    except Exception as e:
        print(f"Error updating game type in {file_path}: {str(e)}")
        return False