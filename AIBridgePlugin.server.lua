-- AI Bridge: provider-neutral bridge between Roblox Studio and AI clients.
local HttpService = game:GetService("HttpService")
local GuiService = game:GetService("GuiService")

local BASE_URL = "https://ai-bridge-cloud.onrender.com"
local TOKEN = plugin:GetSetting("AIBridgeCloudToken") or ""
local PAIR_CODE = plugin:GetSetting("AIBridgePairCode") or ""
local POLL_INTERVAL = 1
local LOGO_ASSET_ID = "rbxassetid://95427397446061"

local toolbar = plugin:CreateToolbar("AI Bridge")
local toggleButton = toolbar:CreateButton(
	"AIBridgeToggle",
	"Open AI Bridge panel",
	LOGO_ASSET_ID
)
toggleButton.ClickableWhenViewportHidden = true

local running = false
local widgetInfo = DockWidgetPluginGuiInfo.new(
	Enum.InitialDockState.Right,
	true,
	false,
	320,
	320,
	290,
	280
)
local widget = plugin:CreateDockWidgetPluginGui("AIBridgePanel", widgetInfo)
widget.Title = "AI Bridge"

local root = Instance.new("Frame")
root.Size = UDim2.fromScale(1, 1)
root.BackgroundColor3 = Color3.fromRGB(24, 27, 36)
root.BorderSizePixel = 0
root.Parent = widget

local padding = Instance.new("UIPadding")
padding.PaddingTop = UDim.new(0, 18)
padding.PaddingBottom = UDim.new(0, 18)
padding.PaddingLeft = UDim.new(0, 18)
padding.PaddingRight = UDim.new(0, 18)
padding.Parent = root

local title = Instance.new("TextLabel")
title.Position = UDim2.fromOffset(38, 0)
title.Size = UDim2.new(1, -38, 0, 32)
title.BackgroundTransparency = 1
title.Font = Enum.Font.GothamBold
title.Text = "AI Bridge"
title.TextColor3 = Color3.fromRGB(245, 247, 255)
title.TextSize = 20
title.TextXAlignment = Enum.TextXAlignment.Left
title.Parent = root

local logo = Instance.new("ImageLabel")
logo.Size = UDim2.fromOffset(30, 30)
logo.BackgroundTransparency = 1
logo.Image = LOGO_ASSET_ID
logo.ScaleType = Enum.ScaleType.Fit
logo.Parent = root

local statusDot = Instance.new("Frame")
statusDot.Position = UDim2.fromOffset(0, 50)
statusDot.Size = UDim2.fromOffset(12, 12)
statusDot.BackgroundColor3 = Color3.fromRGB(148, 155, 170)
statusDot.BorderSizePixel = 0
statusDot.Parent = root
Instance.new("UICorner", statusDot).CornerRadius = UDim.new(1, 0)

local statusLabel = Instance.new("TextLabel")
statusLabel.Position = UDim2.fromOffset(22, 42)
statusLabel.Size = UDim2.new(1, -22, 0, 28)
statusLabel.BackgroundTransparency = 1
statusLabel.Font = Enum.Font.GothamMedium
statusLabel.Text = "Bridge disconnected"
statusLabel.TextColor3 = Color3.fromRGB(190, 195, 207)
statusLabel.TextSize = 15
statusLabel.TextXAlignment = Enum.TextXAlignment.Left
statusLabel.Parent = root

local activeAIName = "No AI client yet"

local clientLabel = Instance.new("TextLabel")
clientLabel.Position = UDim2.fromOffset(0, 76)
clientLabel.Size = UDim2.new(1, 0, 0, 22)
clientLabel.BackgroundTransparency = 1
clientLabel.Font = Enum.Font.GothamBold
clientLabel.Text = "Active AI: " .. activeAIName
clientLabel.TextColor3 = Color3.fromRGB(111, 188, 255)
clientLabel.TextSize = 13
clientLabel.TextXAlignment = Enum.TextXAlignment.Left
clientLabel.Parent = root

local tokenLabel = Instance.new("TextLabel")
tokenLabel.Position = UDim2.fromOffset(0, 106)
tokenLabel.Size = UDim2.new(1, 0, 0, 20)
tokenLabel.BackgroundTransparency = 1
tokenLabel.Font = Enum.Font.GothamMedium
tokenLabel.Text = "Pairing code"
tokenLabel.TextColor3 = Color3.fromRGB(172, 178, 195)
tokenLabel.TextSize = 12
tokenLabel.TextXAlignment = Enum.TextXAlignment.Left
tokenLabel.Parent = root

local tokenInput = Instance.new("TextBox")
tokenInput.Position = UDim2.fromOffset(0, 130)
tokenInput.Size = UDim2.new(1, 0, 0, 36)
tokenInput.BackgroundColor3 = Color3.fromRGB(36, 41, 55)
tokenInput.BorderSizePixel = 0
tokenInput.ClearTextOnFocus = false
tokenInput.Font = Enum.Font.Code
tokenInput.PlaceholderText = "Click Connect to generate a code"
tokenInput.PlaceholderColor3 = Color3.fromRGB(115, 122, 142)
tokenInput.Text = PAIR_CODE
tokenInput.TextColor3 = Color3.fromRGB(226, 231, 244)
tokenInput.TextSize = 22
tokenInput.TextXAlignment = Enum.TextXAlignment.Center
tokenInput.Visible = true
tokenInput.TextEditable = false
tokenInput.Parent = root
Instance.new("UICorner", tokenInput).CornerRadius = UDim.new(0, 8)

local tokenPadding = Instance.new("UIPadding")
tokenPadding.PaddingLeft = UDim.new(0, 10)
tokenPadding.PaddingRight = UDim.new(0, 10)
tokenPadding.Parent = tokenInput

local openPairButton = Instance.new("TextButton")
openPairButton.Position = UDim2.fromOffset(0, 176)
openPairButton.Size = UDim2.new(1, 0, 0, 38)
openPairButton.BackgroundColor3 = Color3.fromRGB(39, 49, 73)
openPairButton.BorderSizePixel = 0
openPairButton.Font = Enum.Font.GothamBold
openPairButton.Text = "Open pairing page"
openPairButton.TextColor3 = Color3.fromRGB(130, 211, 255)
openPairButton.TextSize = 13
openPairButton.Visible = PAIR_CODE ~= ""
openPairButton.Parent = root
Instance.new("UICorner", openPairButton).CornerRadius = UDim.new(0, 9)

local connectionButton = Instance.new("TextButton")
connectionButton.Position = UDim2.new(0, 0, 1, -52)
connectionButton.Size = UDim2.new(1, 0, 0, 46)
connectionButton.BackgroundColor3 = Color3.fromRGB(66, 111, 255)
connectionButton.BorderSizePixel = 0
connectionButton.Font = Enum.Font.GothamBold
connectionButton.Text = "Connect"
connectionButton.TextColor3 = Color3.new(1, 1, 1)
connectionButton.TextSize = 16
connectionButton.AutoButtonColor = true
connectionButton.Parent = root
Instance.new("UICorner", connectionButton).CornerRadius = UDim.new(0, 10)

local function setStatus(kind, message)
	statusLabel.Text = message
	if kind == "connected" then
		statusDot.BackgroundColor3 = Color3.fromRGB(57, 211, 126)
		connectionButton.BackgroundColor3 = Color3.fromRGB(198, 66, 80)
		connectionButton.Text = "Disconnect"
	elseif kind == "connecting" then
		statusDot.BackgroundColor3 = Color3.fromRGB(255, 184, 55)
		connectionButton.BackgroundColor3 = Color3.fromRGB(92, 103, 130)
		connectionButton.Text = "Connecting..."
	else
		statusDot.BackgroundColor3 = Color3.fromRGB(148, 155, 170)
		connectionButton.BackgroundColor3 = Color3.fromRGB(66, 111, 255)
		connectionButton.Text = "Connect"
	end
end

local function headers()
	return { ["Content-Type"] = "application/json", ["Authorization"] = "Bearer " .. TOKEN }
end

local function request(method, path, body)
	local response = HttpService:RequestAsync({
		Url = BASE_URL .. path,
		Method = method,
		Headers = headers(),
		Body = body and HttpService:JSONEncode(body) or nil,
	})
	if not response.Success then
		error(("HTTP %d: %s"):format(response.StatusCode, response.Body))
	end
	return HttpService:JSONDecode(response.Body)
end

local function tryPair()
	setStatus("connecting", "Registering with AI Bridge Cloud...")
	local ok, response = pcall(function()
		local result = HttpService:RequestAsync({
			Url = BASE_URL .. "/v1/plugins/register",
			Method = "POST",
			Headers = { ["Content-Type"] = "application/json" },
			Body = HttpService:JSONEncode({ name = "Roblox Studio - " .. game.Name }),
		})
		if not result.Success then error("Pairing unavailable") end
		return HttpService:JSONDecode(result.Body)
	end)
	if ok and response.plugin_token and response.pairing_code then
		TOKEN = response.plugin_token
		PAIR_CODE = response.pairing_code
		tokenInput.Text = PAIR_CODE
		openPairButton.Visible = true
		plugin:SetSetting("AIBridgeCloudToken", TOKEN)
		plugin:SetSetting("AIBridgePairCode", PAIR_CODE)
		setStatus("connecting", "Enter code " .. PAIR_CODE .. " on the pairing page")
		return true
	end
	setStatus("disconnected", "Cloud unavailable - check HTTP requests")
	return false
end

local function splitPath(path)
	local parts = {}
	for part in string.gmatch(path, "[^/]+") do
		table.insert(parts, part)
	end
	return parts
end

local function resolve(path)
	if path == "game" or path == "" then return game end
	local parts = splitPath(path)
	local current = game
	if parts[1] == "game" then table.remove(parts, 1) end
	for _, name in ipairs(parts) do
		current = current:FindFirstChild(name)
		if not current then error("Path not found: " .. path) end
	end
	return current
end

local function decodeValue(value)
	if type(value) ~= "table" or not value.__type then return value end
	if value.__type == "Vector3" then return Vector3.new(value.x, value.y, value.z) end
	if value.__type == "Vector2" then return Vector2.new(value.x, value.y) end
	if value.__type == "Color3" then return Color3.fromRGB(value.r, value.g, value.b) end
	if value.__type == "CFrame" then return CFrame.new(table.unpack(value.components)) end
	if value.__type == "UDim2" then
		return UDim2.new(value.xScale, value.xOffset, value.yScale, value.yOffset)
	end
	if value.__type == "Enum" then
		local enumType = Enum[value.enum]
		if not enumType then error("Unknown enum: " .. tostring(value.enum)) end
		return enumType[value.item]
	end
	error("Unsupported typed value: " .. tostring(value.__type))
end

local function instancePath(instance)
	if instance == game then return "game" end
	local names = {}
	local current = instance
	while current and current ~= game do
		table.insert(names, 1, current.Name)
		current = current.Parent
	end
	return "game/" .. table.concat(names, "/")
end

local function describe(instance, depth)
	local output = { name = instance.Name, className = instance.ClassName, path = instancePath(instance) }
	if depth > 0 then
		output.children = {}
		for _, child in ipairs(instance:GetChildren()) do
			table.insert(output.children, describe(child, depth - 1))
		end
	end
	return output
end

local actions = {}

function actions.ping(_args)
	return { placeId = game.PlaceId, placeName = game.Name }
end

function actions.get_tree(args)
	return describe(resolve(args.path or "game"), math.clamp(args.depth or 2, 0, 8))
end

function actions.create_instance(args)
	local parent = resolve(args.parent or "game/Workspace")
	local className = assert(args.className, "className is required")
	local instance = Instance.new(className)
	instance.Name = args.name or instance.ClassName
	for property, value in pairs(args.properties or {}) do
		instance[property] = decodeValue(value)
	end
	instance.Parent = parent
	return describe(instance, 0)
end

function actions.set_properties(args)
	local instance = resolve(assert(args.path, "path is required"))
	for property, value in pairs(assert(args.properties, "properties are required")) do
		instance[property] = decodeValue(value)
	end
	return describe(instance, 0)
end

function actions.move_instance(args)
	local instance = resolve(assert(args.path, "path is required"))
	instance.Parent = resolve(assert(args.newParent, "newParent is required"))
	return describe(instance, 0)
end

function actions.delete_instance(args)
	local instance = resolve(assert(args.path, "path is required"))
	if instance == game then error("Cannot delete game") end
	local oldPath = instancePath(instance)
	instance:Destroy()
	return { deleted = oldPath }
end

local function execute(command)
	local action = actions[command.action]
	if not action then error("Unsupported action: " .. tostring(command.action)) end
	return action(command.args or {})
end

local function sendResult(id, ok, data)
	request("POST", "/v1/plugin/result/" .. id, { ok = ok, data = data })
end

local function pollLoop()
	if TOKEN == "" and not tryPair() then
		running = false
		return
	end
	setStatus("connecting", "Connecting to AI Bridge Cloud...")
	local failures = 0
	while running do
		local ok, response = pcall(request, "GET", "/v1/plugin/poll")
		if ok and response.command then
			failures = 0
			local command = response.command
			activeAIName = tostring(command.client or "Unknown AI client")
			clientLabel.Text = "Active AI: " .. activeAIName
			setStatus("connected", "Command received")
			local executed, result = pcall(execute, command)
			pcall(sendResult, command.id, executed, executed and result or tostring(result))
		elseif ok and response.paired then
			failures = 0
			PAIR_CODE = ""
			tokenInput.Text = "Connected"
			openPairButton.Visible = false
			plugin:SetSetting("AIBridgePairCode", "")
			setStatus("connected", "Cloud connected - waiting for AI")
		elseif ok then
			failures = 0
			PAIR_CODE = tostring(response.pairing_code or PAIR_CODE)
			tokenInput.Text = PAIR_CODE
			openPairButton.Visible = PAIR_CODE ~= ""
			plugin:SetSetting("AIBridgePairCode", PAIR_CODE)
			setStatus("connecting", "Enter code " .. PAIR_CODE .. " on the pairing page")
		elseif not ok then
			failures += 1
			setStatus("connecting", "Cloud unavailable - retrying...")
			warn("[AI Bridge] " .. tostring(response))
			if failures >= 4 then
				TOKEN = ""
				plugin:SetSetting("AIBridgeCloudToken", "")
				if tryPair() then failures = 0 end
			end
		end
		task.wait(POLL_INTERVAL)
	end
	setStatus("disconnected", "Bridge disconnected")
end

local function toggleConnection()
	running = not running
	if running then
		print("[AI Bridge] Connecting to " .. BASE_URL)
		task.spawn(pollLoop)
	else
		print("[AI Bridge] Disconnected")
		setStatus("disconnected", "Bridge disconnected")
	end
end

connectionButton.Activated:Connect(toggleConnection)

openPairButton.Activated:Connect(function()
	if PAIR_CODE == "" then return end
	local url = BASE_URL .. "/connect?code=" .. PAIR_CODE
	local ok = pcall(function() GuiService:OpenBrowserWindow(url) end)
	if not ok then
		warn("[AI Bridge] Open this URL in your browser: " .. url)
	end
end)

toggleButton.Click:Connect(function()
	widget.Enabled = not widget.Enabled
end)

plugin.Unloading:Connect(function()
	running = false
end)

task.defer(function()
	widget.Enabled = true
	running = true
	task.spawn(pollLoop)
end)
