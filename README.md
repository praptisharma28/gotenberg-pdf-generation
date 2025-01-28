# gotenberg-pdf-generation
A FastAPI application for PDF generation using Gotenberg.

## Prerequisites

Make sure you have the following installed on your system:
- Python 3.7 or higher
- pip (Python package manager)

---

## Setup Instructions

### 1. Clone the Repository

Clone this repository to your local machine:

```bash
git clone https://github.com/praptisharma28/gotenberg-pdf-generation.git
)
cd gotenberg-pdf-generation
```

### 2. Create a Virtual Environment

Create a virtual environment to isolate the dependencies:

```bash
python3 -m venv venv
```

Activate the virtual environment:
- **For Linux/Mac**:
  ```bash
  source venv/bin/activate
  ```
- **For Windows**:
  ```bash
  venv\Scripts\activate
  ```

### 3. Install Dependencies

### 4. Run the FastAPI Application

Start the FastAPI application using `uvicorn`:

```bash
uvicorn app.main:app --reload
```

- Replace `app.main:app` with the correct module and app name if your structure is different.
- By default, the application will run on `http://127.0.0.1:8000`.


## API Documentation

FastAPI provides interactive API documentation by default. You can access it in your browser:
- Swagger UI: `http://127.0.0.1:8000/docs`
- ReDoc: `http://127.0.0.1:8000/redoc`

---

## Deactivating the Virtual Environment

Once you are done, deactivate the virtual environment:

```bash
deactivate
```

---

## License

This project is licensed under the MIT License.
