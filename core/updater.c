#include <windows.h>
#include <stdio.h>
#include <stdlib.h>

int main(int argc, char *argv[]) {
    if (argc != 4) {
        printf("Usage: updater.exe <zip_path> <install_dir> <main_process_pid>\n");
        return 1;
    }
    
    char *zip_path = argv[1];
    char *install_dir = argv[2];
    int main_pid = atoi(argv[3]);
    
    printf("Terminating main process (PID: %d)...\n", main_pid);
    
    // python please die
    HANDLE hProcess = OpenProcess(PROCESS_TERMINATE, FALSE, main_pid);
    if (hProcess) {
        TerminateProcess(hProcess, 0);
        CloseHandle(hProcess);
        printf("Main process terminated\n");
    } else {
        printf("Warning: Could not open main process for termination\n");
    }
    
    // pray to windows gods that this process is gone
    Sleep(2000);

    char cmd[2048];
    snprintf(cmd, sizeof(cmd), "tar -xf \"%s\" -C \"%s\"", zip_path, install_dir);
    
    printf("Extracting update to %s...\n", install_dir);
    int result = system(cmd);
    
    if (result == 0) {
        printf("Update extracted successfully!\n");

        if (DeleteFile(zip_path)) {
            printf("Cleaned up zip file\n");
        }

        char restart_cmd[1024];
        snprintf(restart_cmd, sizeof(restart_cmd), 
            "cd /d \"%s\\casual-preloader\" && python main.py", install_dir);
        
        printf("Restarting application...\n");
        system(restart_cmd);
        
    } else {
        printf("ERROR: Failed to extract update (exit code: %d)\n", result);
        printf("Press any key to exit...\n");
        getchar();
    }
    
    return 0;
}