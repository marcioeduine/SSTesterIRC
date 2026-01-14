#include <iostream>
#include <string>
#include <vector>
#include <cstdlib>

void ss_git_push(void)
{
    // git add .
    system("git add .");
    
    // git diff --name-only --cached
    FILE* pipe = popen("git diff --name-only --cached", "r");
    if (!pipe) return;
    
    std::vector<std::string> files;
    char buffer[1024];
    std::string file_content;
    
    while (fgets(buffer, sizeof(buffer), pipe) != NULL) {
        std::string line = buffer;
        // Remove trailing newline
        if (!line.empty() && line[line.size()-1] == '\n') {
            line.erase(line.size()-1);
        }
        files.push_back(line);
    }
    pclose(pipe);
    
    if (!files.empty()) {
        std::string msg = "UPDATED FILE:\n";
        
        for (size_t i = 0; i < files.size(); ++i) {
            // Check for SS_COMMIT comments
            FILE* f = fopen(files[i].c_str(), "r");
            if (f) {
                std::vector<std::string> comments;
                char line_buffer[1024];
                
                while (fgets(line_buffer, sizeof(line_buffer), f) != NULL) {
                    std::string line = line_buffer;
                    // Remove trailing newline
                    if (!line.empty() && line[line.size()-1] == '\n') {
                        line.erase(line.size()-1);
                    }
                    
                    // Check for // SS_COMMIT: or #// SS_COMMIT:
                    size_t pos = line.find("// SS_COMMIT:");
                    if (pos == std::string::npos) {
                        pos = line.find("#// SS_COMMIT:");
                    }
                    
                    if (pos != std::string::npos) {
                        // Extract comment after SS_COMMIT:
                        std::string comment = line.substr(pos + 13); // 13 = len("// SS_COMMIT:")
                        
                        // Trim leading whitespace
                        size_t first_non_space = comment.find_first_not_of(" \t");
                        if (first_non_space != std::string::npos) {
                            comment = comment.substr(first_non_space);
                            comments.push_back(comment);
                        }
                    }
                }
                fclose(f);
                
                if (!comments.empty()) {
                    msg += "\n\n - " + files[i] + ":";
                    for (size_t j = 0; j < comments.size(); ++j) {
                        msg += "\n   • " + comments[j];
                    }
                } else {
                    msg += "\n - " + files[i];
                }
            }
        }
        
        // git commit -m "$msg"
        std::string command = "git commit -m \"" + msg + "\"";
        system(command.c_str());
    } else {
        std::cout << "Nothing to commit!" << std::endl;
    }
}

int	main(void)
{
	return (ss_git_push(), 0);
}
