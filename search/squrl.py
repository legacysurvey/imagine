"""
squrl.py
This python module enables parsing of requests in SQURL, an SQL URL. It handles the conversion of the SQURL query portion of a URL to an SQL query
Version 0.4
Annette Greiner, NERSC DAS, 3/30/15
========
Suppose your web app receives a request for http://mydomain.com/api/uri_fragment
This module handles a uri_fragment, of the form
mytable/expression/PRED[/expression][/CONJ/expression/PRED[/expression]]
where mytable is the table to query, and expression can be of the form
value[/OP/value]
where value can be the name of a column (mycolumn), a column plus an array index (mycolumn.2), a numeric value, or a simple string.
OP (operation) can be DIV, TIMES, PLUS, or MINUS
CONJ (conjunction) can be AND or OR
PRED (predicate) can be EQ, NEQ, LT, LTE, GT, GTE, LIKE, NOTLIKE, ISNULL, or ISNOTNULL
Parentheses can be used at the beginning or end of a value to control the order of operations.

e.g.
Candidate/DECAM_FLUX.2/GT/0.631
becomes
SELECT * FROM candidate WHERE DECAM_FLUX[2] > 0.631

Candidate/DECAM_FLUX.2/DIV/DECAM_MW_TRANSMISSION.2/GT/0.631/AND/DECAM_FLUX.4/DIV/DECAM_MW_TRANSMISSION.4/GT/DECAM_FLUX.2/DIV/DECAM_MW_TRANSMISSION.2/TIMES/4.365 
becomes
SELECT * FROM candidate WHERE DECAM_FLUX[2] / DECAM_MW_TRANSMISSION[2] > 0.631 AND DECAM_FLUX[4] / DECAM_MW_TRANSMISSION[4] > DECAM_FLUX[2] / DECAM_MW_TRANSMISSION[2] * 4.365

To use SQURL, you'll need to configure the tables that users can query and the limit on rows returned, below
"""

import re
import custom_check

# Basic configuration: in the columns dict below, enter the name of each table that you want to allow queries against as a key, 
# then for each table, enter a list of the columns you want to be queriable as its value.

# problem: these need to be a list to get ordering
config_columns = {
    'candidate': [
        'brickid',
        'objid',
        'blob',
        'type',
        'ra',
        'ra_ivar',
        'dec',
        'dec_ivar',
        'bx',
        'by',
        'bx0',
        'by0',
        'ebv',
        'dchisq1',
        'dchisq2',
        'dchisq3',
        'dchisq4',
        'fracdev',
        'fracdev_ivar',
        'shapeexp_r',
        'shapeexp_r_ivar',
        'shapeexp_e1',
        'shapeexp_e1_ivar',
        'shapeexp_e2',
        'shapeexp_e2_ivar',
        'shapeexp_r',
        'shapedev_r_ivar',
        'shapedev_e1',
        'shapedev_e1_ivar',
        'shapedev_e2',
        'shapedev_e2_ivar',
        # 'decam_flux',
        # 'decam_flux_ivar',
        # 'decam_apflux',
        # 'decam_apflux_resid',
        # 'decam_apflux_ivar',
        # 'decam_mw_transmission',
        # 'decam_nobs',
        # 'decam_rchi2',
        # 'decam_fracflux',
        # 'decam_fracmasked',
        # 'decam_fracin',
        # 'decam_saturated',
        # 'out_of_bounds',
        # 'decam_anymask',
        # 'decam_allmask',
        # 'wise_flux',
        # 'wise_flux_ivar',
        # 'wise_mw_transmission',
        # 'wise_nobs',
        # 'wise_fracflux',
        # 'wise_rchi2',
        # 'dchisq',
        # 'fracdev',
        # 'fracdev_ivar',
        # 'shapeexp_r',
        # 'shapeexp_r_ivar',
        # 'shapeexp_e1',
        # 'shapeexp_e1_ivar',
        # 'shapeexp_e2',
        # 'shapeexp_e2_ivar',
        # 'shapedev_r',
        # 'shapedev_r_ivar',
        # 'shapedev_e1',
        # 'shapedev_e1_ivar',
        # 'shapedev_e2',
        # 'shapedev_e2_ivar',
        # 'ebv',
        # 'sdss_run',
        # 'sdss_camcol',
        # 'sdss_field',
        # 'sdss_id',
        # 'sdss_objid',
        # 'sdss_parent',
        # 'sdss_nchild',
        # 'sdss_objc_type',
        # 'sdss_objc_flags',
        # 'sdss_objc_flags2',
        # 'sdss_flags',
        # 'sdss_flags2',
        # 'sdss_tai',
        # 'sdss_ra',
        # 'sdss_ra_ivar',
        # 'sdss_dec',
        # 'sdss_dec_ivar',
        # 'sdss_psf_fwhm',
        # 'sdss_mjd',
        # 'sdss_theta_dev',
        # 'sdss_theta_deverr',
        # 'sdss_ab_dev',
        # 'sdss_ab_deverr',
        # 'sdss_theta_exp',
        # 'sdss_theta_experr',
        # 'sdss_ab_exp',
        # 'sdss_ab_experr',
        # 'sdss_fracdev',
        # 'sdss_phi_dev_deg',
        # 'sdss_phi_exp_deg',
        # 'sdss_psfflux',
        # 'sdss_psfflux_ivar',
        # 'sdss_cmodelflux',
        # 'sdss_cmodelflux_ivar',
        # 'sdss_modelflux',
        # 'sdss_modelflux_ivar',
        # 'sdss_devflux',
        # 'sdss_devflux_ivar',
        # 'sdss_expflux',
        # 'sdss_expflux_ivar',
        # 'sdss_extinction',
        # 'sdss_calib_status',
        # 'sdss_resolve_status',
        ]
    }
# If some of the db tables contain arrays, list them below. For each one, enter a dict with the name of the table as the key
# and a dict containing column names and max array indices as its value.
config_arrays = {
    'Tractor': {
    'decam_flux': 4,
    'decam_mw_transmission': 4,
    }
}

# Set the maximum number of rows to return, '' if no limit
limit = '10'

# End of basic configuration


def unsqurl(instring):
    result = {"returncode": '200', "error": "", "sql": ""}

    try:
        instring = instring.upper()
        badchar = re.search(r'([;\s\"\'@-])', instring)
        if badchar: 
            result['error'] = "Oops, there is a character in the URI that is not allowed: \"" + badchar.group(1) + "\""
            result['returncode'] = "400"
            return result

        # convert table and column names in config_columns to lower case, in columns var
        columns = {}
        for key in config_columns:
            columns_list = config_columns[key]
            uc_cols = []
            for col in columns_list:
                uc_cols.append(col.upper())
            columns[key.upper()] = uc_cols
        # convert table and column names in config_arrays to lower case, in arrays var
        arrays = {}
        for key in config_arrays:
            array_dict = config_arrays[key]
            uc_dict = {}
            for arraykey in array_dict:
                uc_dict[arraykey.upper()] = array_dict[arraykey]
            arrays[key.upper()] = uc_dict
        #determine the table name
        table, squrlstring = instring.split('/', 1)
        if(table in columns):
            # make a list of columns to return from the dict of allowed columns
            col_items = columns[table]
            col_list = ", ".join(col_items)
            result['sql'] = "SELECT " + col_list + " FROM " + table + " WHERE "
        else:
            result['error'] = "No known table was found in the query."
            result['returncode'] = "400"
            return result
        #break urlstring into statements by conjunction
        statements = []
        conjunctions = []
        splits = re.split(r'(\/AND\/|\/OR\/)', squrlstring)
        if splits == -1:
            statements.append(squrlstring)
        else:
            for i in range (0, len(splits)):
                if i%2 == 0: statements.append(splits[i])
                else: conjunctions.append(splits[i])
        for statement in statements:
            # Uncomment the lines below to use custom checks. To do so, create a function check_custom(statement) that returns 
            # a dictionary like that in the result variable
            print(statement)
            custom_result = custom_check.check_custom(statement)
            if custom_result['returncode'] != '200':
                return custom_result
            elif custom_result['sql'] != '':
                result['sql'] += custom_result['sql']
                # break out of the statement processing
                continue
            # keep checking if custom check didn't find an error but didn't return some sql
            # basic checks
            columnpresent = False # check on whether a column name is given in the statement; initially assume no column is mentioned
            stringpresent = False # check on whether string is used with a compatible predicate
            numberpresent = False # check on whether a number is used with a compatible predicate
            #add the conjunction to the SQL query, if there is one
            stindex = statements.index(statement)
            if stindex > 0 and len(conjunctions) >= stindex:
                #switch
                if conjunctions[stindex - 1] == "/AND/":
                    result['sql'] += " AND "
                elif conjunctions[stindex - 1] == "/OR/":
                    result['sql'] += " OR "
            #break statement into expressions by predicate
            expressions = []
            predicates = []
            ssplits = re.split(r'(\/EQ\/|\/NEQ\/|\/LT\/|\/LTE\/|\/GT\/|\/GTE\/|\/LIKE\/|\/NOTLIKE\/|\/ISNULL\/|\/ISNULL|\/ISNOTNULL\/|\/ISNOTNULL)', statement)
            if ssplits == -1:
                expressions.append(statement)
            else:
                for j in range (0, len(ssplits)):
                    if j%2 == 0: expressions.append(ssplits[j])
                    else: predicates.append(ssplits[j])
            for expression in expressions:
                # add the predicate to the SQL query, if there is one
                expindex = expressions.index(expression)
                if expindex > 0 and len(predicates) >= expindex:
                    #switch
                    if predicates[expindex - 1] == "/EQ/":
                        result['sql'] += " = "
                    elif predicates[expindex - 1] == "/NEQ/":
                        result['sql'] += " != "
                    elif predicates[expindex - 1] == "/LT/":
                        result['sql'] += " < "
                    elif predicates[expindex - 1] == "/LTE/":
                        result['sql'] += " <= "
                    elif predicates[expindex - 1] == "/GT/":
                        result['sql'] += " > "
                    elif predicates[expindex - 1] == "/GTE/":
                        result['sql'] += " >= "
                    elif predicates[expindex - 1] == "/LIKE/":
                        result['sql'] += " LIKE "
                    elif predicates[expindex - 1] == "/NOTLIKE/":
                        result['sql'] += " NOT LIKE "
                    elif predicates[expindex - 1] == "/ISNULL/":
                        result['sql'] += " IS NULL"
                    elif predicates[expindex - 1] == "/ISNULL":
                        result['sql'] += " IS NULL"
                    elif predicates[expindex - 1] == "/ISNOTNULL/":
                        result['sql'] += " IS NOT NULL"
                    elif predicates[expindex - 1] == "/ISNOTNULL":
                        result['sql'] += " IS NOT NULL"
                #break expressions into values by operation
                values=[]
                operations=[]
                esplits = re.split(r'(\/DIV\/|\/TIMES\/|\/PLUS\/|\/MINUS\/)', expression)
                if esplits == -1:
                    values.append(expression)
                else:
                    for k in range(0, len(esplits)):
                        if k%2 == 0: values.append(esplits[k])
                        else: operations.append(esplits[k])
                #add the expressions to the SQL query
                for m in range(0, len(values)):
                    if  m > 0 and len(operations) >= m:
                        #switch
                        if operations[m-1] == "/DIV/":
                                result['sql'] += " / "
                        elif operations[m-1] == "/TIMES/":
                                result['sql'] += " * "
                        elif operations[m-1] == "/MINUS/":
                                result['sql'] += " - "
                        elif operations[m-1] == "/PLUS/":
                                result['sql'] += " + "
                    #add the values to the SQL query
                    leftparen = rightparen = ''
                    if values[m].startswith('('):
                        leftparen = '('
                        thevalue = values[m][1:]
                    elif values[m].endswith(')'):
                        rightparen = ')'
                        thevalue = values[m][:-1]
                    else: thevalue = values[m]
                    result['sql'] += leftparen # the empty string if it doesn't start with a paren
                    isempty = re.match(r'', thevalue)
                    isalphanum = re.match(r'([a-zA-Z_][a-zA-Z0-9_%]+)$', thevalue)
                    hasarray = re.match(r'([a-zA-Z_][a-zA-Z0-9_]+)\.(\d+)$', thevalue)
                    isnumeric = re.match(r'-?[\d\.]+$', thevalue)
                    if hasarray:
                        #a column name plus array index
                        column = hasarray.group(1)
                        index = hasarray.group(2)
                        if column in columns[table] and int(index) <= arrays[table][column]:
                            result['sql'] += column + "[" + index + "]"
                            columnpresent = True
                        else:
                            result['error'] = "Column " + column + " with array index " + index + " not found in the specified table."
                            result['returncode'] = "400"
                            return result
                    elif isalphanum:
                        if thevalue in columns[table]:
                            #a column name
                            if arrays[table][thevalue] == None:
                                result['sql'] += thevalue
                                columnpresent = True
                            else: 
                                result['error'] = "Column " + thevalue + " requires an array index."
                                result['returncode'] = "400"
                                return result
                        else:
                            #not a column name, treat as a string
                            if expindex > 0 and predicates[expindex-1] not in ['/LIKE/', '/NOTLIKE/']:
                                result['error'] = predicates[expindex-1]  + " must be followed by a numeric value."
                                result['returncode'] = "400"
                                return result
                            else: 
                                result['sql']+="'" + thevalue + "'"
                                stringpresent = True
                    elif isnumeric:
                        #an integer or float
                        if float(thevalue) == 0 and operations[m-1] == "/DIV/": 
                            result['error'] = "Division by zero is not allowed."
                            result['returncode'] = "400"
                            return result
                        else: 
                            result['sql'] += thevalue
                            numberpresent = True
                    elif isempty:
                        # predicate takes no object
                        if predicates[expindex-1] in ['/ISNULL/', '/ISNULL', '/ISNOTNULL/', '/ISNOTNULL']: result['sql']+=''
                        else: 
                            result['error'] = "Got an empty value where there should have been something: near " + predicates[expindex-1]
                            result['returncode'] = "400"
                            return result
                    else:
                        #sadface
                        result['error'] = thevalue + " is not a usable value nor a column in the specified table."
                        result['returncode'] = "400"
                        return result
                    result['sql'] += rightparen # the empty string if no right paren
            # if no column name turned up in the statement
            if columnpresent == False: 
                result['error'] = "Each statement must reference a column in the specified table"
                result['returncode'] = "400"
                return result
            if stringpresent == True and predicates[0] not in ['/LIKE/', '/NOTLIKE/']: 
                result['error'] = "Strings cannot be used with predicates other than LIKE and NOTLIKE."
                result['returncode'] = "400"
                return result
            if numberpresent == True and predicates[0] in ['/LIKE/','/NOTLIKE/']: 
                result['error'] = "Numbers cannot be used with LIKE and NOTLIKE."
                result['returncode'] = "400"
                return result
        if limit != '': result['sql']+=' LIMIT ' + limit + ';'
    except:
        result['returncode'] = '500'
        result['error'] = "An error occurred. Unable to parse the URI string."
        return result

    return result
