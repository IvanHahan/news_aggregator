# News Aggregator

A Python-based news aggregation and processing system that collects news and research papers from various sources, processes them using AI, and publishes summaries to configured channels.

## 🚀 Features

- **Multiple Content Sources**: Aggregates content from:
  - VentureBeat AI news
  - ArXiv research papers
  - Hugging Face trending papers
  - Telegram channels
  - Google News (via custom search)

- **AI-Powered Processing**: 
  - Content summarization using OpenAI GPT models
  - Link content extraction and analysis
  - Intelligent content filtering

- **Multi-Platform Publishing**:
  - Telegram bot integration
  - Extensible publisher architecture

- **Data Management**:
  - MongoDB database integration
  - Duplicate content filtering
  - Automatic cleanup of old entries

## 📋 Prerequisites

- Python 3.8+
- MongoDB database
- OpenAI API key
- Telegram API credentials (for Telegram integration)
- Google Search API key (optional, for Google News)

## 🛠️ Installation

1. **Clone the repository**:
   ```bash
   git clone https://github.com/IvanHahan/news_aggregator.git
   cd news_aggregator
   ```

2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Set up environment variables**:
   Create a `.env` file in the root directory with the following variables:
   ```env
   # OpenAI Configuration
   OPENAI_API_KEY=your_openai_api_key_here
   
   # Telegram Configuration
   TELEGRAM_API_ID=your_telegram_api_id
   TELEGRAM_API_HASH=your_telegram_api_hash
   TELEGRAM_BOT_TOKEN=your_telegram_bot_token
   
   # Database Configuration (MongoDB)
   MONGODB_URI=mongodb://localhost:27017/news_aggregator
   
   # Optional: Google Search API
   GOOGLE_SEARCH_API_KEY=your_google_search_api_key
   ```

## 🚀 Usage

### Running Locally

```bash
python src/main.py
```

### Deployment with Railway

The project includes a `railway.toml` configuration file for easy deployment:

```bash
railway up
```

## 🏗️ Architecture

The project follows a modular architecture with clear separation of concerns:

```
src/
├── main.py                 # Entry point
├── content_maker.py        # Main orchestrator
├── data_model.py          # Data structures (News, Paper, etc.)
├── db.py                  # Database operations
├── news_summarizer.py     # AI content processing
├── link_explorer.py       # Web content extraction
├── google_search.py       # Google Search integration
├── aggregators/           # Content source implementations
│   ├── base_aggregator.py
│   ├── arxiv_aggregator.py
│   ├── google_news_aggregator.py
│   ├── hf_trending_papers_aggregator.py
│   ├── telegram_aggregator.py
│   └── venture_beat_aggregator.py
└── publishers/            # Publishing platform implementations
    ├── base_publisher.py
    └── telegram_publisher.py
```

### Key Components

- **ContentMaker**: Main orchestrator that coordinates aggregation, processing, and publishing
- **Aggregators**: Collect content from various sources (ArXiv, VentureBeat, etc.)
- **Publishers**: Distribute processed content to different platforms
- **NewsSummarizer**: AI-powered content processing and summarization
- **NewsDatabase**: MongoDB integration for content storage and deduplication

## 🔧 Configuration

### Adding New Aggregators

1. Create a new class extending `BaseAggregator`
2. Implement the `poll()` method returning a list of `News` or `Paper` objects
3. Add the aggregator to the `ContentMaker.build()` method

### Adding New Publishers

1. Create a new class extending `BasePublisher`
2. Implement the `publish()` method
3. Add the publisher to the `ContentMaker.build()` method

## 📦 Dependencies

- **langchain & langchain-openai**: AI/ML processing
- **beautifulsoup4**: Web scraping
- **requests**: HTTP requests
- **telethon**: Telegram API integration
- **pymongo**: MongoDB database operations
- **faiss-cpu**: Vector similarity search
- **loguru**: Advanced logging
- **python-dotenv**: Environment variable management

## 🔐 Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `OPENAI_API_KEY` | OpenAI API key for content processing | Yes |
| `TELEGRAM_API_ID` | Telegram API ID | Yes (for Telegram) |
| `TELEGRAM_API_HASH` | Telegram API hash | Yes (for Telegram) |
| `TELEGRAM_BOT_TOKEN` | Telegram bot token | Yes (for Telegram) |
| `MONGODB_URI` | MongoDB connection string | Yes |
| `GOOGLE_SEARCH_API_KEY` | Google Search API key | No |

## 📝 Data Models

The system uses structured data models for different content types:

- **News**: Title, summary, and link
- **Paper**: Academic papers with authors, publication dates, and abstracts
- **LinkContent**: Web page content extraction results

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🐛 Troubleshooting

### Common Issues

1. **MongoDB Connection Error**: Ensure MongoDB is running and the connection string is correct
2. **API Rate Limits**: Check your API quotas for OpenAI and other services
3. **Telegram Authentication**: Verify your Telegram API credentials are correct
4. **Missing Dependencies**: Run `pip install -r requirements.txt` to ensure all dependencies are installed

### Logging

The application uses `loguru` for comprehensive logging. Check the logs for detailed error information and debugging.

## 🔄 Workflow

1. **Aggregation**: Collect content from configured sources
2. **Filtering**: Remove duplicate content using database queries
3. **Processing**: Summarize and enhance content using AI
4. **Publishing**: Distribute processed content to configured channels
5. **Cleanup**: Remove old entries to maintain database efficiency

---

**Note**: This is an automated content aggregation system. Please ensure compliance with the terms of service of all integrated platforms and APIs.