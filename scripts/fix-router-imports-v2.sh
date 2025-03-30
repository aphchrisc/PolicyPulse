#!/bin/bash

# Fix React Router imports for v7
# This script updates imports from 'react-router-dom' and 'react-router/dom' to 'react-router'

echo "Updating React Router imports for v7..."

# Fix react-router-dom imports
echo "Step 1: Updating react-router-dom imports to react-router..."
find src -type f -name "*.jsx" -exec sed -i '' "s/from ['|\"]react-router-dom['|\"]/from 'react-router'/g" {} \;

# Fix react-router/dom imports
echo "Step 2: Updating react-router/dom imports to react-router..."
find src -type f -name "*.jsx" -exec sed -i '' "s/from ['|\"]react-router\/dom['|\"]/from 'react-router'/g" {} \;

# Special case for RouterProvider and createBrowserRouter
echo "Step 3: Fixing RouterProvider and createBrowserRouter imports..."
find src -type f -name "App.jsx" -exec sed -i '' "s/RouterProvider, createBrowserRouter/createBrowserRouter/g" {} \;
find src -type f -name "App.jsx" -exec sed -i '' "s/from 'react-router'/from 'react-router'\nimport { RouterProvider } from 'react-router\/dom'/g" {} \;

echo "Import update complete. Make sure to restart your development server." 