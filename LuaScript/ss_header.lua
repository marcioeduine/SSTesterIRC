local function get_formatted_date()
    return os.date("%Y/%m/%d %H:%M:%S")
end

local function truncate_filename(filename, max_length)
    if #filename > max_length then
        filename = filename:sub(1, max_length - 3) .. "..."
    end
    return string.format("%-" .. max_length .. "s", filename)
end

local function build_header(filename, created_date, updated_date)
    local lines = {
        "/* ************************************************************************** */",
        "/*                                                                            */",
        "/*                                                       ::::::::   ::::::::  */",
        "/*    " .. filename .. "       :+:    :+: :+:    :+:  */",
        "/*                                                    +:+        +:+          */",
        "/*    By: Ser Superior <marcioeduine@gmail.com>      +#++:++#++ +#++:++#++    */",
        "/*                                                         +#+        +#+     */",
        "/*    Created: " .. created_date .. " by Ser Superior #+#    #+# #+#    #+#      */",
        "/*    Updated: " .. updated_date .. " by Ser Superior ########   ########        */",
        "/*                                                                            */",
        "/* ************************************************************************** */",
    }
    
    return lines
end

local function header_exists()
    local lines = vim.api.nvim_buf_get_lines(0, 0, 12, false)
    for _, line in ipairs(lines) do
        if line:match("Created:") then
            return true
        end
    end
    return false
end

local function update_header_date()
    local lines = vim.api.nvim_buf_get_lines(0, 0, 12, false)
    local updated_date = get_formatted_date()
    
    for i, line in ipairs(lines) do
        if line:match("Updated:") then
            lines[i] = line:gsub("Updated: %d%d%d%d/%d%d/%d%d %d%d:%d%d:%d%d", "Updated: " .. updated_date)
            vim.api.nvim_buf_set_lines(0, i - 1, i, false, {lines[i]})
            return
        end
    end
end

local function insert_ssheader()
    local filename = vim.fn.expand("%:t")
    filename = truncate_filename(filename, 42)
    
    if header_exists() then
        update_header_date()
        return
    end
    
    local created_date = get_formatted_date()
    local updated_date = get_formatted_date()
    local header_lines = build_header(filename, created_date, updated_date)
    vim.api.nvim_buf_set_lines(0, 0, 0, false, header_lines)
end

vim.api.nvim_create_user_command("SSHeader", insert_ssheader, {})
vim.keymap.set("n", "<F4>", insert_ssheader, { desc = "Insert custom ss_header" })

return {}
