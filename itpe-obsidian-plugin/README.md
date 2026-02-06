# ITPE Obsidian Plugin

Obsidian plugin for ITPE Topic Enhancement System integration. Validates topics and provides enhancement proposals.

## Installation

1. Clone this repository
2. Install dependencies:

```bash
npm install
```

3. Build the plugin:

```bash
npm run build
```

4. Copy the plugin files to your Obsidian vault:

- Copy `main.js`, `manifest.json` to `.obsidian/plugins/itpe-topic-enhancement/`
- Enable the plugin in Obsidian settings

## Development

### Watch Mode

For development with hot-reload:

```bash
npm run dev
```

### Build Production

```bash
npm run build
```

### Testing

```bash
# Run tests
npm test

# Run tests with UI
npm run test:ui

# Run tests with coverage
npm run test:coverage
```

## Project Structure

```
itpe-obsidian-plugin/
├── src/
│   ├── main.ts              # Plugin entry point
│   ├── settings.ts          # Settings management
│   ├── commands.ts          # Command definitions
│   ├── api/
│   │   ├── client.ts        # Backend API client
│   │   └── types.ts         # API type definitions
│   ├── parsers/
│   │   ├── topic-parser.ts  # Topic file parser
│   │   └── dataview.ts      # Dataview integration
│   ├── ui/
│   │   ├── status-bar.ts    # Status bar
│   │   ├── result-modal.ts  # Validation result modal
│   │   ├── proposal-modal.ts# Proposal modal
│   │   └── settings-tab.ts  # Settings tab
│   ├── sync/
│   │   └── state-sync.ts    # State synchronization
│   └── utils/
│       ├── cache.ts         # Cache management
│       └── logger.ts        # Logging utility
├── manifest.json            # Plugin manifest
├── package.json
├── tsconfig.json
└── esbuild.config.mjs
```

## Features

- **Topic Export**: Export topics as JSON for backend processing
- **Validation**: Validate topic completeness and quality
- **Proposals**: View and apply enhancement proposals
- **Status Bar**: Real-time validation status display
- **Auto Sync**: Automatic periodic synchronization
- **Dataview Integration**: Seamless integration with Dataview plugin

## Commands

- `ITPE: Export Topics` - Export all topics as JSON
- `ITPE: Validate Current Topic` - Validate the currently open topic
- `ITPE: Validate All Topics` - Validate all topics in vault
- `ITPE: Show Validation Result` - Display validation results
- `ITPE: Show Proposals` - View enhancement proposals
- `ITPE: Open Dashboard` - Open web dashboard

## Configuration

Configure the plugin in Obsidian settings:

- **Backend URL**: URL of the ITPE backend API (default: http://localhost:8000)
- **API Key**: Optional API key for authentication
- **Auto Sync**: Enable automatic synchronization
- **Sync Interval**: Interval for auto-sync in minutes (default: 5)
- **Show Status Bar**: Display status in status bar
- **Debug Mode**: Enable detailed logging
- **Domain Folders**: Comma-separated list of domain folders

## Backend API

The plugin requires a running backend API with the following endpoints:

- `POST /api/v1/topics/upload` - Upload topics
- `POST /api/v1/validate/` - Create validation task
- `GET /api/v1/validate/task/{id}` - Get validation status
- `GET /api/v1/validate/task/{id}/result` - Get validation result
- `GET /api/v1/proposals` - Get enhancement proposals
- `PATCH /api/v1/topics/{id}` - Apply proposal

## License

MIT

## Author

turtlesoup0
