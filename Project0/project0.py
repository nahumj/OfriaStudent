def convert_to_capitals(input_filename, output_filename):
    """
    Takes a two paths denoting input and output files.
    This function should read in a file, 
    convert all lowercase letters to uppercase,
    then output to output_file.
    """
    contents = open(input_filename, 'r').read()
    open(output_filename, 'w').write(contents)

