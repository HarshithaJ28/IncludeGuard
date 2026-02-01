#include "database.h"
#include <iostream>
#include <algorithm>

// Forward declaration example - only uses pointer
class Database;  // This is what we want to recommend

void processDatabase(Database* db) {
    // Only uses pointer, doesn't need full definition
}

void runQuery(Database* db, const std::string& sql) {
    // Another pointer usage
}
