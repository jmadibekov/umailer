# Umailer

Umailer is an app that connects to an IMAP server, reads emails, and downloads attachments.

## Getting Started Locally

To start the app, initialize [Poetry](https://python-poetry.org/), set up environment variables by creating .env file (follow example.env) and run the following from the root of the repo:

```sh
uvicorn app.main:app
```

Check the interactive API docs at [http://127.0.0.1:8000/redoc](http://127.0.0.1:8000/redoc) or at [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs) to see what requests you can send to the app.

## Technologies Used

- **FastAPI:** The main web-framework the app uses to produce RESTful APIs.

- **Poetry:** Dependency manager for Python projects.

Python 3.8.5 is the default language of the project.

## Improvements

Following is the list of main improvements I would work on before releasing:

- Dockerize the app
- Add tests
- Add Continues Integration (CI)

## Raising Issues

At the time of writing this, everything was working perfectly on my computer. That being said, I understand some
might face unexpected errors or difficulties to run the app eventually.

So please feel free to raise an issue with the problem that you faced (I'll answer all of them) or contact me via
[email](mailto:jmadibekov@gmail.com).
