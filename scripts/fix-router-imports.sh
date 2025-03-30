#!/bin/bash

# Fix React Router imports for v7
# This script updates imports from 'react-router-dom' to 'react-router\/dom'

echo "Updating React Router imports for v7..."
find src -type f -name "*.jsx" -exec sed -i '' "s/from ['|\"]react-router-dom['|\"]/from 'react-router\/dom'/g" {} \;

echo "Import update complete. Make sure to restart your development server." 