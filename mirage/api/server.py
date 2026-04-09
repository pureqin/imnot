"""
FastAPI application factory.

Responsibilities:
- Create and configure the FastAPI app instance.
- Accept a list of PartnerDefinition objects and delegate route registration
  to the dynamic router.
- Initialize the session store (database setup) on application startup.
- Expose the app object for Uvicorn to serve.
"""
