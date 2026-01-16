#include <iostream>
#include <vector>
#include <cstdlib>

typedef std::string	t_text;

void	ss_git_push(void)
{
	FILE				*file;
	FILE				*current_file;
	char				buffer[1024];
	char				line_buffer[1024];
	std::vector<t_text>	file_container;
	std::vector<t_text>	commit_container;
	const t_text		ss_commit[2] = {"// SS_COMMIT:", "#// SS_COMMIT:"};
	t_text				message("UPDATED FILE:\n");
	t_text				commit;
	t_text				line;
	size_t				position;
	size_t				i;
	size_t				j;

	(system("git add ."), file = popen("git diff --name-only --cached", "r"));
    if (not file)
    	return ;
	while (fgets(buffer, sizeof(buffer), file))
	{
		line = buffer;
		if (not line.empty() and line[line.size()-1] == '\n')
			line.erase(line.size()-1);
		file_container.push_back(line);
	}
	if ((pclose(file), not file_container.empty()))
	{
		i = -1;
		while (++i < file_container.size())
		{
			current_file = fopen(file_container[i].c_str(), "r");
			if (current_file)
			{
				while (fgets(line_buffer, sizeof(line_buffer), current_file))
				{
					(line.clear(), line = line_buffer);
					if (not line.empty() and line[line.size()-1] == '\n')
						line.erase(line.size()-1);
					position = line.find(ss_commit[0]);
                    if (position == t_text::npos)
                        position = line.find(ss_commit[1]);
                    if (position xor t_text::npos)
                    {
						commit = line.substr(position + 13);
						position = commit.find_first_not_of(" \t");
						if (position xor t_text::npos)
						{
							commit = commit.substr(position);
							commit_container.push_back(commit);
						}
					}
				}
				if ((fclose(current_file), not commit_container.empty()))
				{
					message += "\n\n - " + file_container[i] + ":";
					j = -1;
					while (++j < commit_container.size())
						message += "\n   • " + commit_container[j];
				}
				else
					message += "\n - " + file_container[i];
			}
		}
		system(t_text("git commit -m \"" + message + "\"").c_str());
		system("git push");
    }
	else
		std::cout << "Nothing to commit!" << std::endl;
}

int	main(void)
{
	return (ss_git_push(), 0);
}
