# EurLex Scraper - Comprehensive Database Data Model

## Conceptual Overview
The data model is designed to capture the complete lifecycle of EU document scraping, from initial retrieval to final storage and analysis. It provides a flexible, normalized structure that supports detailed tracking of document metadata, content, and scraping processes.

## Database Relationship Diagram

```
+-------------------+        +---------------------+
|    documents      |        | document_contents   |
+-------------------+        +---------------------+
| PK: id            |<---1:1-| FK: document_id     |
| celex_number      |        | full_text           |
| title             |        | summary             |
| document_type     |        | keywords            |
| date_published    |        | text_hash           |
| source_url        |        +---------------------+
| raw_json_path     |
| language          |        +---------------------+
| created_at        |        | document_metadata   |
| updated_at        |        +---------------------+
+-------------------+        | FK: document_id     |
         |                   | scrape_session_id   |
         |                   | processing_status   |
         |                   | validation_errors   |
         |                   | retry_count         |
         |                   | storage_size_bytes  |
         |                   +---------------------+
         |                            |
         |                            |
         v                            v
+-------------------+
| scrape_sessions   |
+-------------------+
| PK: id            |
| start_time        |
| end_time          |
| total_documents   |
| success_count     |
| error_count       |
| script_version    |
+-------------------+
```

## Detailed Table Specifications

### 1. `documents` Table
#### Purpose
The central table storing core document information, serving as the primary reference point for all document-related data.

#### Detailed Column Specifications
- `id`: 
  - Unique, auto-incrementing primary key
  - Serves as the primary reference for all related tables
  - Ensures referential integrity across the database

- `celex_number`: 
  - Unique identifier for EU documents
  - Follows EU's official CELEX numbering system
  - Enables precise document tracking and retrieval
  - Example format: `32020R1234`

- `title`: 
  - Full official title of the document
  - Supports multilingual titles
  - Stored as TEXT to accommodate lengthy titles

- `document_type`: 
  - Categorizes documents by EU legal instrument
  - Predefined set of values:
    - Regulation
    - Directive
    - Decision
    - Recommendation
    - Opinion
  - Enables filtering and analysis by document category

- `date_published`: 
  - Official publication date
  - Supports historical and chronological analysis
  - Indexed for efficient querying

- `source_url`: 
  - Original source of the document
  - Enables traceability and potential re-scraping
  - Stored as TEXT to support long URLs

- `raw_json_path`: 
  - File system path to original scraped JSON
  - Maintains link to raw data
  - Supports data provenance and potential reprocessing

- `language`: 
  - Document's primary language
  - Uses ISO 639-1 two-letter codes (e.g., 'en', 'fr')
  - Supports multilingual document tracking

- `created_at` & `updated_at`:
  - Automatic timestamp tracking
  - Enables auditing and change tracking

### 2. `document_contents` Table
#### Purpose
Stores the complete textual content and derived information for each document.

#### Key Features
- 1:1 relationship with `documents` table
- Separates large text data from core document metadata
- Supports full-text search and content analysis

#### Unique Columns
- `text_hash`: 
  - SHA-256 hash of document text
  - Enables quick deduplication
  - Supports identifying unique or modified documents

- `keywords`: 
  - Extracted or manually assigned keywords
  - Comma-separated or JSON-formatted list
  - Enhances searchability and categorization

### 3. `document_metadata` Table
#### Purpose
Tracks processing metadata, validation status, and scraping session details.

#### Processing Workflow Tracking
- `processing_status`: 
  - Tracks document's processing state
  - Enum values: 
    - 'pending'
    - 'processed'
    - 'error'
  - Enables monitoring and error handling

- `validation_errors`: 
  - Stores detailed error information
  - JSON or text format
  - Supports debugging and quality control

- `retry_count`: 
  - Tracks scraping attempt history
  - Helps identify problematic documents
  - Supports adaptive scraping strategies

### 4. `scrape_sessions` Table
#### Purpose
Provides a comprehensive record of each scraping session.

#### Session Tracking Features
- Captures start and end times
- Tracks overall session performance
- Enables longitudinal analysis of scraping processes

#### Performance Metrics
- `total_documents_processed`
- `success_count`
- `error_count`
- `script_version`

## Relationship Dynamics

### 1:1 Relationships
- Each `documents` record has exactly one corresponding record in:
  - `document_contents`
  - `document_metadata`

### Foreign Key Relationships
- `document_metadata.document_id` references `documents.id`
- `document_contents.document_id` references `documents.id`
- `document_metadata.scrape_session_id` references `scrape_sessions.id`

## Advanced Query Patterns

### Document Retrieval
```sql
SELECT d.*, dc.full_text, dm.processing_status
FROM documents d
JOIN document_contents dc ON d.id = dc.document_id
JOIN document_metadata dm ON d.id = dm.document_id
WHERE d.document_type = 'Regulation' 
  AND dm.processing_status = 'processed';
```

### Scraping Session Analysis
```sql
SELECT 
    ss.id, 
    ss.start_time, 
    ss.total_documents,
    AVG(dm.storage_size_bytes) as avg_document_size
FROM scrape_sessions ss
JOIN document_metadata dm ON ss.id = dm.scrape_session_id
GROUP BY ss.id;
```

## Recommended Database Configurations
- **PostgreSQL**: Recommended for complex queries, full-text search
- **MySQL/MariaDB**: Alternative with good performance
- **Indexing**: Create indexes on foreign keys and frequently queried columns

## Implementation Considerations
1. Use database migrations for schema management
2. Implement ORM for language-specific abstractions
3. Design robust error handling
4. Plan for horizontal scaling
5. Implement data retention and archiving policies

## Future Enhancements
- Add full-text search capabilities
- Implement document versioning
- Create advanced analytics views
- Support more granular language tracking

## Data Integrity Constraints
- Enforce referential integrity
- Use transactions for batch operations
- Implement soft delete mechanisms
- Regular data validation checks

## Performance Optimization
- Partition large tables by date or document type
- Use appropriate indexing strategies
- Consider read replicas for analytics workloads
- Implement caching mechanisms

## Security Considerations
- Use role-based access control
- Encrypt sensitive metadata
- Implement audit logging
- Comply with data protection regulations
